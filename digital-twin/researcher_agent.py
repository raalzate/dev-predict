import spade
from spade.behaviour import CyclicBehaviour
import json
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import re
import time
import os

class ResearcherAgent(spade.agent.Agent):
    """
    Agente que investiga en la web para encontrar información relevante 
    sobre un tema, extrae el contenido y lo resume.
    """
    def __init__(self, jid, password, stack_file):
        super().__init__(jid, password)
        self.stack_file = stack_file
        self.tech_stack = []

    class ResearchBehav(CyclicBehaviour):

        def _generate_technical_queries(self, title, keywords):
            """
            Traduce y enriquece las palabras clave para crear consultas técnicas 
            más efectivas en inglés, usando el stack tecnológico del proyecto.
            """
            translation_map = {
                'exportar': ['export', 'generate'], 'reporte': ['report'], 'ventas': ['sales'], 'pdf': ['pdf'],
                'carga': ['upload'], 'avatar': ['avatar', 'profile picture'], 'perfil': ['profile'], 's3': ['s3'],
                'login': ['login', 'authentication'], 'usuario': ['user'], 'api': ['api'], 'externa': ['external'],
                'pago': ['payment', 'checkout'], 'stripe': ['stripe'], 'paypal': ['paypal'],
                'base de datos': ['database', 'db'], 'migración': ['migration'], 'optimización': ['optimization'],
            }
            
            # Usar el tech_stack cargado en lugar de una lista hardcodeada
            tech_context = self.agent.tech_stack + ['library', 'tutorial', 'example', 'best practices']
            
            english_keywords = set()
            for keyword in keywords:
                if keyword in translation_map:
                    english_keywords.update(translation_map[keyword])

            if not english_keywords:
                return [title]

            generated_queries = set()
            if len(english_keywords) > 1:
                 generated_queries.add(" ".join(sorted(list(english_keywords))))

            for keyword in english_keywords:
                for context in tech_context:
                    generated_queries.add(f"{keyword} {context}")
                    # Búsquedas más específicas con el stack principal
                    if self.agent.tech_stack:
                        main_tech = self.agent.tech_stack[0] # Asumir que el primero es el más relevante
                        generated_queries.add(f"{main_tech} {keyword} {context}")

            return [title] + sorted(list(generated_queries), key=len, reverse=True)


        def _get_content_from_url(self, url):
            """Obtiene y limpia el texto de los párrafos de una URL."""
            try:
                response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status() 
                soup = BeautifulSoup(response.text, 'html.parser')
                paragraphs = [p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'code', 'pre'])]
                if not paragraphs: return None
                full_text = ' '.join(paragraphs)
                return re.sub(r'\s+', ' ', full_text).strip()
            except requests.RequestException as e:
                print(f"[Researcher] ERROR: No se pudo acceder a la URL {url}. Razón: {e}")
                return None

        def _summarize_text(self, text, keywords, num_sentences=4):
            """
            Extrae las oraciones más relevantes de un texto basándose en la 
            presencia de palabras clave.
            """
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
            scored_sentences = {}
            all_keywords = set(keywords)
            
            # Generar todas las posibles palabras clave de búsqueda para puntuar mejor
            translated_keywords = self._generate_technical_queries("", keywords)
            all_keywords.update(translated_keywords)

            for sentence in sentences:
                score = sum(1 for keyword in all_keywords if keyword.lower() in sentence.lower())
                if score > 0:
                    scored_sentences[sentence[:150]] = (score, sentence)

            if not scored_sentences:
                return "No se encontraron frases relevantes con las palabras clave."

            best_sentences = sorted(scored_sentences.values(), key=lambda x: x[0], reverse=True)
            return ' '.join([s[1] for s in best_sentences[:num_sentences]])

        async def run(self):
            msg = await self.receive(timeout=10)
            if msg and msg.metadata.get("performative") == "request":
                data = json.loads(msg.body)
                title = data.get('title', 'N/A')
                initial_keywords = data.get('queries', [])
                
                print(f"[Researcher] Recibida solicitud de investigación para '{title}' sobre: {initial_keywords}")
                
                smart_queries = self._generate_technical_queries(title, initial_keywords)
                print(f"[Researcher] Consultas técnicas generadas con stack del proyecto: {smart_queries}")
                
                all_content = ""
                found_anything = False
                
                for i, query in enumerate(smart_queries[:5]):
                    try:
                        print(f"[Researcher] ... Buscando '{query}' en la web...")
                        num_res = 3 if i == 0 else 1
                        search_results = list(search(query, num_results=num_res, lang="en"))
                        
                        if search_results:
                            found_anything = True
                            for url in search_results:
                                content = self._get_content_from_url(url)
                                if content: all_content += content + " "
                                time.sleep(1) 

                    except Exception as e:
                        print(f"[Researcher] ERROR durante la búsqueda para '{query}': {e}")

                if found_anything and all_content:
                    final_summary = self._summarize_text(all_content, initial_keywords)
                    findings = {"summary": final_summary}
                else:
                    findings = {"summary": "No se encontraron resultados de búsqueda relevantes para los términos clave."}
                
                print(f"[Researcher] Enviando hallazgos para '{title}'.")
                reply = spade.message.Message(
                    to=str(msg.sender),
                    body=json.dumps(findings),
                    metadata={"performative": "inform"},
                    thread=msg.thread
                )
                await self.send(reply)

    async def setup(self):
        print("[Researcher] Agente de investigación iniciado.")
        try:
            with open(self.stack_file, 'r') as f:
                self.tech_stack = json.load(f).get('technologies', [])
            if self.tech_stack:
                print(f"[Researcher] Stack tecnológico cargado: {self.tech_stack}")
            else:
                print("[Researcher] WARNING: No se encontró stack tecnológico en 'tech_stack.json'. Usando contexto genérico.")
        except FileNotFoundError:
            print("[Researcher] WARNING: No se encontró el archivo 'tech_stack.json'. Usando contexto genérico.")
        except json.JSONDecodeError:
            print("[Researcher] ERROR: El archivo 'tech_stack.json' tiene un formato inválido.")

        self.add_behaviour(self.ResearchBehav())

