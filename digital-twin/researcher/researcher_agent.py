import spade
from spade.behaviour import CyclicBehaviour
import json
import aiohttp
import asyncio
import re
import logging
import os
from typing import List, Set, Dict
from config import GOOGLE_API_KEY, GOOGLE_CX
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import ssl
import socket
import certifi


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ResearcherAgent")

class ResearcherAgent(spade.agent.Agent):
    """Un agente que realiza investigaciones web utilizando la API oficial de Google Search."""

    def __init__(self, jid: str, password: str, config: Dict = None):
        super().__init__(jid, password)
        self.config = config or {}
        
        # Carga las credenciales de forma segura desde las variables de entorno
        self.config.setdefault("google_api_key", GOOGLE_API_KEY)
        self.config.setdefault("google_cx", GOOGLE_CX)
        self.config.setdefault("stack_file", "researcher/tech_stack.json")
        self.config.setdefault("request_timeout", 15)
        self.config.setdefault("max_results_per_query", [3, 1])
        self.config.setdefault("max_sentences_summary", 4)
        self.config.setdefault("search_delay", 0.5) 
        
        self.tech_stack: List[str] = []
       

    async def setup(self) -> None:
        """Configura el agente, verifica las claves de API, carga el tech stack y añade el comportamiento."""
        logger.info(f"[ResearcherAgent] Iniciando agente '{self.jid}'.")
        
        # Verificación de credenciales al iniciar
        if not self.config.get("google_api_key") or not self.config.get("google_cx"):
            logger.critical("[ResearcherAgent] FATAL: GOOGLE_API_KEY o GOOGLE_CX no están configuradas.")
            logger.critical("Por favor, configúralas como variables de entorno antes de ejecutar.")
            await self.stop()
            return

        await self._load_tech_stack()
        self.add_behaviour(self.ResearchBehav())

    async def _load_tech_stack(self) -> None:
        """Carga el tech stack desde un archivo JSON."""
        stack_file = self.config.get("stack_file", "researcher/tech_stack.json")
        try:
            with open(stack_file, 'r') as f:
                self.tech_stack = json.load(f).get('technologies', [])
            if self.tech_stack:
                logger.info(f"[ResearcherAgent] Tech stack cargado: {self.tech_stack}")
        except FileNotFoundError:
            logger.error(f"[ResearcherAgent] Archivo de tech stack '{stack_file}' no encontrado.")
        except json.JSONDecodeError:
            logger.error(f"[ResearcherAgent] Formato JSON inválido en '{stack_file}'.")

    class ResearchBehav(CyclicBehaviour):
        """Comportamiento cíclico para manejar las solicitudes de investigación."""

        def _generate_technical_queries(self, title: str, keywords: List[str]) -> List[str]:
            if not keywords:
                return [title]

            processed_keywords: Set[str] = {k.lower() for k in keywords}
            generated_queries: Set[str] = set()

            # Construir el contexto global del stack (ordenado para consistencia)
            stack_context = " ".join(sorted(self.agent.tech_stack)) if self.agent.tech_stack else ""

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

        def _get_content_from_url(self, url: str) -> str | None:
            try:

                with  Stealth().use_sync(sync_playwright()) as p:
                    browser = p.chromium.launch(
                        channel="chrome",
                        headless=True,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-infobars",
                            "--disable-dev-shm-usage",
                        ]
                    )
                    page = browser.new_page()

                    page.set_extra_http_headers({
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/123.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9"
                    })

                    page.goto(url, wait_until="domcontentloaded")
                    page.mouse.move(200, 300)
                    page.wait_for_timeout(2000)

                    html = page.content()
                    browser.close()

                    soup = BeautifulSoup(html, 'html.parser')
                    target_elements = soup.find_all(class_='post-layout')
                    if not target_elements:
                        return None

                    paragraphs = []
                    for elem in target_elements:
                        # Limpiar elementos irrelevantes dentro de cada bloque
                        for tag in elem(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                            tag.decompose()

                        # Extraer texto de etiquetas importantes
                        elements = elem.find_all(['p', 'h1', 'h2', 'h3', 'code', 'pre', 'li'])
                        paragraphs.extend([e.get_text(separator=' ', strip=True) for e in elements])

                    if not paragraphs:
                        return None

                    full_text = ' '.join(paragraphs)
                    return re.sub(r'\s+', ' ', full_text).strip()

            except Exception as e:
                logger.warning(f"[ResearcherAgent] Error al obtener contenido dinámico de {url}: {e}")
                return None

        def _summarize_text(self, text: str, keywords: List[str], num_sentences: int = 4) -> str:
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
            all_keywords = set(keywords)
            translated_keywords = self._generate_technical_queries("", keywords)
            all_keywords.update([q for q in translated_keywords if q])
            scored_sentences = {}
            for i, sentence in enumerate(sentences):
                if len(sentence) > 10: 
                    score = sum(1 for keyword in all_keywords if keyword.lower() in sentence.lower())
                    if score > 0:
                        scored_sentences[i] = (score, sentence)
            if not scored_sentences:
                return "No se encontraron frases relevantes para las palabras clave proporcionadas."
            best_sentences = sorted(scored_sentences.values(), key=lambda x: x[0], reverse=True)
            return ' '.join(s[1] for s in best_sentences[:num_sentences])

        async def _search_with_google_api(self, query: str, num_results: int) -> List[str]:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.agent.config["google_api_key"],
                'cx': self.agent.config["google_cx"],
                'q': query,
                'num': num_results
            }

            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(family=socket.AF_INET, ssl=ssl_context)

            try:
                async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
                    async with session.get(url, params=params, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            return [item['link'] for item in data.get('items', [])]
                        else:
                            error_text = await response.text()
                            logger.error(f"[ResearcherAgent] Google API Error ({response.status}): {error_text}")
                            return []
            except aiohttp.ClientSSLError as e:
                logger.error(f"[ResearcherAgent] Error SSL: {e}")
            except Exception as e:
                logger.error(f"[ResearcherAgent] Error de conexión: {e}")
            return []

        async def run(self) -> None:
            msg = await self.receive(timeout=30)
            if not msg:
                return
            try:
                data = json.loads(msg.body)
                title = data.get('title', 'N/A')
                initial_keywords = data.get('queries', [])
                thread_id = msg.thread

                logger.info(f"[{thread_id}] Solicitud de investigación recibida para '{title}'")
                smart_queries = self._generate_technical_queries(title, initial_keywords)
                logger.info(f"[{thread_id}] Consultas técnicas generadas: {smart_queries}")

                all_content = ""
                found_anything = False
                processed_urls = set()

                for i, query in enumerate(smart_queries[:5]):
                    num_results = self.agent.config["max_results_per_query"][0 if i == 0 else 1]
                    search_results = await self._search_with_google_api(query, num_results)
                    logger.info(f"[{thread_id}] Se encontraron {len(search_results)} resultados para '{query}'")
                    if search_results:
                        found_anything = True
                        for url in search_results:
                            if url not in processed_urls:
                                processed_urls.add(url)
                                loop = asyncio.get_running_loop()
                                logger.info(f"Processing URL: {url}")
                                content = await loop.run_in_executor(None, self._get_content_from_url, url)
                                if content: all_content += content + ", "
                                await asyncio.sleep(self.agent.config["search_delay"])
                
                summary = (self._summarize_text(all_content, initial_keywords, self.agent.config["max_sentences_summary"])
                           if found_anything and all_content
                           else "No se encontraron resultados de búsqueda relevantes para las palabras clave proporcionadas.")

                logger.info(f"[{thread_id}] Enviando hallazgos para '{title}'.")
                reply = spade.message.Message(to=str(msg.sender), body=json.dumps({"summary": summary}), metadata={"performative": "inform"}, thread=msg.thread)
                await self.send(reply)
            except Exception as e:
                logger.error(f"Error fatal en el comportamiento de investigación: {e}", exc_info=True)