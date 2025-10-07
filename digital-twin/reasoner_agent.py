import spade
from spade.behaviour import FSMBehaviour, State
# La importación de Template ya no es necesaria aquí
import json
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

# --- Estados de la Máquina de Estados (FSM) ---
STATE_RECEIVE_STORY = "RECEIVE_STORY"
STATE_REQUEST_ML = "REQUEST_ML"
STATE_WAIT_FOR_ML = "WAIT_FOR_ML"
STATE_REQUEST_RESEARCH = "REQUEST_RESEARCH"
STATE_WAIT_FOR_RESEARCH = "WAIT_FOR_RESEARCH"
STATE_REASON_WITH_GEMINI = "REASON_WITH_GEMINI"
STATE_FINALIZE = "FINALIZE"
STATE_HANDLE_FAILURE = "HANDLE_FAILURE"

# Cargar la clave de API desde el archivo .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("[Reasoner] ERROR: La variable de entorno GEMINI_API_KEY no fue encontrada.")
    print("[Reasoner] Por favor, crea un archivo .env con tu clave.")

class ReasonerAgent(spade.agent.Agent):
    
    class ReasonerFSM(FSMBehaviour):
        async def on_start(self):
            print("[Reasoner] FSM iniciado. Esperando por una historia de usuario...")

        async def on_end(self):
            # Usamos get con un valor por defecto para evitar errores si el título no se estableció
            title = self.get('story_title') or "una historia desconocida"
            print(f"[Reasoner] FSM finalizado para la historia: {title}")
    
    async def setup(self):
        print("[Reasoner] Agente razonador iniciado. Creando FSM.")
        fsm = self.ReasonerFSM()

        # --- Definición de los Estados ---
        fsm.add_state(name=STATE_RECEIVE_STORY, state=ReceiveStoryState(), initial=True)
        fsm.add_state(name=STATE_REQUEST_ML, state=RequestMLEstimateState())
        fsm.add_state(name=STATE_WAIT_FOR_ML, state=WaitForMLResponseState())
        fsm.add_state(name=STATE_REQUEST_RESEARCH, state=RequestResearchState())
        fsm.add_state(name=STATE_WAIT_FOR_RESEARCH, state=WaitForResearchResponseState())
        fsm.add_state(name=STATE_REASON_WITH_GEMINI, state=ReasonWithGeminiState())
        fsm.add_state(name=STATE_FINALIZE, state=FinalizeEstimationState())
        fsm.add_state(name=STATE_HANDLE_FAILURE, state=HandleFailureState())

        # --- Definición de las Transiciones ---
        fsm.add_transition(source=STATE_RECEIVE_STORY, dest=STATE_REQUEST_ML)
        fsm.add_transition(source=STATE_REQUEST_ML, dest=STATE_WAIT_FOR_ML)
        fsm.add_transition(source=STATE_WAIT_FOR_ML, dest=STATE_REQUEST_RESEARCH)
        fsm.add_transition(source=STATE_WAIT_FOR_ML, dest=STATE_HANDLE_FAILURE) # Si ML falla
        fsm.add_transition(source=STATE_REQUEST_RESEARCH, dest=STATE_WAIT_FOR_RESEARCH)
        fsm.add_transition(source=STATE_WAIT_FOR_RESEARCH, dest=STATE_REASON_WITH_GEMINI)
        fsm.add_transition(source=STATE_REASON_WITH_GEMINI, dest=STATE_FINALIZE)
        fsm.add_transition(source=STATE_REASON_WITH_GEMINI, dest=STATE_HANDLE_FAILURE) # Si Gemini falla
        fsm.add_transition(source=STATE_FINALIZE, dest=STATE_RECEIVE_STORY) # Listo para la siguiente
        fsm.add_transition(source=STATE_HANDLE_FAILURE, dest=STATE_RECEIVE_STORY) # Fallo gestionado, listo para la siguiente

        self.add_behaviour(fsm)

class ReceiveStoryState(State):
    async def run(self):
        # Este estado ahora simplemente espera cualquier mensaje de solicitud
        msg = await self.receive(timeout=1000) 
        if msg and msg.metadata.get("performative") == "request":
            story_data = json.loads(msg.body)
            self.set("story_data", story_data)
            self.set("story_title", story_data.get('title'))
            self.set("original_sender", str(msg.sender))
            self.set("thread_id", msg.thread)
            print(f"[Reasoner] FSM: Iniciando proceso para '{self.get('story_title')}' (Thread: {msg.thread})")
            self.set_next_state(STATE_REQUEST_ML)

class RequestMLEstimateState(State):
    async def run(self):
        print(f"[Reasoner] FSM: Solicitando estimación ML para '{self.get('story_title')}'")
        msg = spade.message.Message(
            to="estimator@localhost",
            body=json.dumps(self.get("story_data")),
            metadata={"performative": "request"},
            thread=self.get("thread_id")
        )
        await self.send(msg)
        self.set_next_state(STATE_WAIT_FOR_ML)

class WaitForMLResponseState(State):
    async def run(self):
        msg = await self.receive(timeout=20) 
        if msg and msg.thread == self.get("thread_id"):
            if msg.metadata.get("performative") == "inform":
                ml_estimate = json.loads(msg.body)
                self.set("ml_estimate", ml_estimate)
                print(f"[Reasoner] FSM: Respuesta ML recibida para '{self.get('story_title')}': {ml_estimate}")
                self.set_next_state(STATE_REQUEST_RESEARCH)
            else:
                print(f"[Reasoner] FSM: ERROR - Se recibió una falla del Agente Estimador.")
                self.set("error_message", "Falla en la estimación de ML.")
                self.set_next_state(STATE_HANDLE_FAILURE)
        elif msg:
            # Ignorar mensajes de otros hilos
            pass
        else:
            print(f"[Reasoner] FSM: ERROR - No se recibió respuesta del Agente Estimador para '{self.get('story_title')}'.")
            self.set("error_message", "Timeout esperando al Agente Estimador.")
            self.set_next_state(STATE_HANDLE_FAILURE)

class RequestResearchState(State):
    async def run(self):
        title = self.get('story_title')
        print(f"[Reasoner] FSM: Solicitando investigación para '{title}'")
        keywords = [word for word in title.lower().split() if len(word) > 3 and word not in ['para', 'con', 'desde']]
        
        msg = spade.message.Message(
            to="researcher@localhost",
            body=json.dumps({"title": title, "queries": keywords}),
            metadata={"performative": "request"},
            thread=self.get("thread_id")
        )
        await self.send(msg)
        self.set_next_state(STATE_WAIT_FOR_RESEARCH)

class WaitForResearchResponseState(State):
    async def run(self):
        msg = await self.receive(timeout=20)
        if msg and msg.thread == self.get("thread_id"):
            research_findings = json.loads(msg.body)
            self.set("research_findings", research_findings)
            print(f"[Reasoner] FSM: Hallazgos de investigación recibidos para '{self.get('story_title')}'")
            self.set_next_state(STATE_REASON_WITH_GEMINI)
        elif msg:
            # Ignorar mensajes de otros hilos
            pass
        else:
            print(f"[Reasoner] FSM: INFO - No se recibió respuesta del Agente Investigador. Continuando sin investigación.")
            self.set("research_findings", {"info": "No se realizó investigación externa."})
            self.set_next_state(STATE_REASON_WITH_GEMINI)

class ReasonWithGeminiState(State):
    async def run(self):
        title = self.get('story_title')
        print(f"[Reasoner] FSM: Razonando con Gemini para '{title}'")
        
        if not GEMINI_API_KEY:
            print("[Reasoner] FSM: ERROR - No hay API Key de Gemini. Usando respuesta simulada.")
            ml_estimate = self.get("ml_estimate") or {"effort": 0, "time": 0}
            simulated_response = {
                "effort_refined": ml_estimate.get('effort', 0) * 1.1,
                "time_estimated": ml_estimate.get('time', 0) * 1.1,
                "complexity": "Media (Simulado)",
                "justification": "Respuesta simulada debido a la falta de API Key."
            }
            self.set("final_estimation", simulated_response)
            self.set_next_state(STATE_FINALIZE)
            return

        prompt = f"""
        Eres un experto en estimación de proyectos de software. Tu tarea es proporcionar una estimación final y detallada para la siguiente historia de usuario, actuando como un 'sanity check' inteligente.
        
        **Historia de Usuario:**
        {json.dumps(self.get('story_data'), indent=2, ensure_ascii=False)}
        
        **Datos de Entrada:**
        1. **Estimación Inicial del Modelo ML (basado en datos históricos):**
           {json.dumps(self.get('ml_estimate'), indent=2)}
        
        2. **Resumen de Investigación (Web Agent):**
           {json.dumps(self.get('research_findings'), indent=2, ensure_ascii=False)}
        
        **Tu Tarea:**
        Basado en TODA la información anterior, analiza los riesgos, la complejidad oculta y el contexto. Luego, proporciona una estimación final.
        Tu respuesta DEBE ser únicamente un objeto JSON válido. Asegúrate de que todos los caracteres especiales dentro de los strings (como saltos de línea o comillas) estén correctamente escapados. La estructura debe ser la siguiente:
        {{
          "effort_refined": <number>,
          "time_estimated": <number>,
          "complexity": "<Low, Medium, High>",
          "justification": "<Detailed explanation of your reasoning, mentioning risks and technical considerations. Be concise but complete.>"
        }}
        """
        
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            
            text_response = response.text
            json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
            
            if json_match:
                json_string = json_match.group(0)
                final_estimation = json.loads(json_string)
                self.set("final_estimation", final_estimation)
                print(f"[Reasoner] FSM: Respuesta de Gemini recibida para '{title}'")
                self.set_next_state(STATE_FINALIZE)
            else:
                raise ValueError("No se encontró un objeto JSON en la respuesta de Gemini.")

        except (json.JSONDecodeError, ValueError, Exception) as e:
            print(f"[Reasoner] FSM: ERROR - Fallo al procesar la respuesta de Gemini: {e}")
            print(f"[Reasoner] Respuesta recibida de Gemini: {response.text if 'response' in locals() else 'No response'}")
            self.set("error_message", "Falla en el razonamiento con Gemini.")
            self.set_next_state(STATE_HANDLE_FAILURE)

class FinalizeEstimationState(State):
    async def run(self):
        title = self.get('story_title')
        print(f"[Reasoner] FSM: Estimación final para '{title}' enviada al Planificador.")
        msg = spade.message.Message(
            to=self.get("original_sender"),
            body=json.dumps(self.get("final_estimation")),
            metadata={"performative": "inform"},
            thread=self.get("thread_id")
        )
        await self.send(msg)
        self.set_next_state(STATE_RECEIVE_STORY)

class HandleFailureState(State):
    async def run(self):
        error_msg = self.get('error_message')
        title = self.get('story_title')
        print(f"[Reasoner] FSM: Gestionando fallo para '{title}'. Error: {error_msg}")
        
        failure_response = {
            "error": True,
            "message": error_msg,
            "story_title": title
        }
        
        msg = spade.message.Message(
            to=self.get("original_sender"),
            body=json.dumps(failure_response),
            metadata={"performative": "failure"},
            thread=self.get("thread_id")
        )
        await self.send(msg)
        self.set_next_state(STATE_RECEIVE_STORY)

