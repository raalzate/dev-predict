import json
import aiohttp
import asyncio
import re
import logging
import ssl
import socket
import certifi
from typing import List, Set, Dict
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from config import GOOGLE_API_KEY, GOOGLE_CX

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResearchService:
    def __init__(self, tech_stack_file: str = 'model/tech_stack.json'):
        if not GOOGLE_API_KEY or not GOOGLE_CX:
            raise ValueError("GOOGLE_API_KEY y GOOGLE_CX deben estar configuradas en las variables de entorno.")
        
        self.google_api_key = GOOGLE_API_KEY
        self.google_cx = GOOGLE_CX
        self.request_timeout = 15
        self.max_results_per_query = [3, 1]
        self.max_sentences_summary = 4
        self.search_delay = 0.5
        self.tech_stack = self._load_tech_stack(tech_stack_file)

    def _load_tech_stack(self, stack_file: str) -> List[str]:
        try:
            with open(stack_file, 'r') as f:
                return json.load(f).get('technologies', [])
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"No se pudo cargar el tech stack desde '{stack_file}'. Se procederá sin él.")
            return []

    def _generate_technical_queries(self, title: str, keywords: List[str]) -> List[str]:
        processed_keywords: Set[str] = {k.lower() for k in keywords}
        generated_queries: Set[str] = set()
        stack_context = " ".join(sorted(self.tech_stack))

        if stack_context:
            generated_queries.add(f"{title} {stack_context}")
        else:
            generated_queries.add(title)

        for keyword in processed_keywords:
            generated_queries.add(f"{keyword} {stack_context}".strip())

        if len(processed_keywords) > 1:
            combined = " ".join(sorted(processed_keywords))
            generated_queries.add(f"{combined} {stack_context}".strip())

        return sorted(list(generated_queries), key=len, reverse=True)

    async def _get_content_from_url(self, url: str) -> str | None:
        try:
            with  Stealth().use_sync(sync_playwright()) as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(url, wait_until="domcontentloaded")
                await page.mouse.move(200, 300)
                await asyncio.sleep(2) # Espera para cualquier renderizado dinámico

                html = await page.content()
                await browser.close()

                soup = BeautifulSoup(html, 'html.parser')
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()

                elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'code', 'pre', 'li'])
                full_text = ' '.join([e.get_text(separator=' ', strip=True) for e in elements])
                return re.sub(r'\s+', ' ', full_text).strip()
        except Exception as e:
            logger.warning(f"Error al obtener contenido de {url}: {e}")
            return None

    def _summarize_text(self, text: str, keywords: List[str]) -> str:
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|?)\s', text)
        all_keywords = set(keywords)
        scored_sentences = {}

        for i, sentence in enumerate(sentences):
            if len(sentence) > 10:
                score = sum(1 for keyword in all_keywords if keyword.lower() in sentence.lower())
                if score > 0:
                    scored_sentences[i] = (score, sentence)

        if not scored_sentences:
            return "No se encontraron frases relevantes para las palabras clave proporcionadas."
        
        best_sentences = sorted(scored_sentences.values(), key=lambda x: x[0], reverse=True)
        return ' '.join(s[1] for s in best_sentences[:self.max_sentences_summary])

    async def _search_with_google_api(self, query: str, num_results: int) -> List[str]:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {'key': self.google_api_key, 'cx': self.google_cx, 'q': query, 'num': num_results}
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, timeout=self.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [item['link'] for item in data.get('items', [])]
                    else:
                        logger.error(f"Error en la API de Google ({response.status}): {await response.text()}")
                        return []
        except Exception as e:
            logger.error(f"Error de conexión durante la búsqueda: {e}")
            return []

    async def conduct_research(self, title: str, keywords: List[str]) -> dict:
        smart_queries = self._generate_technical_queries(title, keywords)
        logger.info(f"Consultas técnicas generadas: {smart_queries}")

        all_content = ""
        processed_urls = set()

        for i, query in enumerate(smart_queries[:3]): # Limitar a 3 consultas para eficiencia
            num_results = self.max_results_per_query[0 if i == 0 else 1]
            search_results = await self._search_with_google_api(query, num_results)

            for url in search_results:
                if url not in processed_urls:
                    processed_urls.add(url)
                    content = await self._get_content_from_url(url)
                    if content:
                        all_content += content + " "
                    await asyncio.sleep(self.search_delay)

        if not all_content:
            summary = "No se pudo encontrar contenido relevante en la web."
        else:
            summary = self._summarize_text(all_content, keywords)
        
        return {"summary": summary}
