import json
import spade
from spade.behaviour import State
import google.generativeai as genai
import logging
from config import AGENT_CONFIG, AgentState
from reasoner.prompt_utils import build_technical_plan_prompt

logger = logging.getLogger("AgentStates")


class ReceiveStoryState(State):
    async def run(self) -> None:
        try:
            msg = await self.receive(timeout=AGENT_CONFIG["initial_receive_timeout"])
            if msg and msg.metadata.get("performative") == "request":
                story_data = json.loads(msg.body)
                self.agent.set("story_data", story_data)
                self.agent.set("story_title", story_data.get('title', 'Sin Título'))
                self.agent.set("original_sender", str(msg.sender))
                self.agent.set("thread_id", msg.thread)
                logger.info(f"Iniciando proceso para '{self.agent.get('story_title')}' (Thread: {msg.thread})")
                self.set_next_state(AgentState.REQUEST_DATA.value)
        except json.JSONDecodeError:
            logger.error(f"Error al decodificar JSON del mensaje: {msg.body}")
        except Exception as e:
            logger.error(f"Error inesperado en ReceiveStoryState: {e}")


class RequestDataInParallelState(State):
    """
    MEJORA: Este estado envía las solicitudes de ML y de investigación en paralelo
    para reducir el tiempo total de espera.
    """
    async def run(self) -> None:
        story_data = self.agent.get("story_data")
        title = self.agent.get("story_title")
        thread_id = self.agent.get("thread_id")
        
        # 1. Solicitud de estimación ML
        logger.info(f"Solicitando estimación ML para '{title}'")
        ml_msg = spade.message.Message(
            to=AGENT_CONFIG["estimator_jid"],
            body=json.dumps(story_data),
            metadata={"performative": "request"},
            thread=thread_id
        )
        await self.send(ml_msg)

        # 2. Solicitud de investigación
        logger.info(f"Solicitando investigación para '{title}'")

        # Lógica de keywords simplificada, se puede mejorar si es necesario
        keywords = [word for word in title.lower().split() if len(word) > 5]
        research_msg = spade.message.Message(
            to=AGENT_CONFIG["researcher_jid"],
            body=json.dumps({"title": title, "queries": keywords}),
            metadata={"performative": "request"},
            thread=thread_id
        )
        await self.send(research_msg)

        self.set_next_state(AgentState.WAIT_FOR_DATA.value)


class WaitForDataState(State):
    """
    MEJORA: Este estado espera ambas respuestas (ML y Research) de forma asíncrona.
    Maneja timeouts y respuestas parciales de manera más elegante.
    """
    async def run(self) -> None:
        ml_estimate = None
        research_findings = None
        
        # Espera por ambas respuestas con un timeout combinado
        timeout = max(AGENT_CONFIG["ml_timeout_seconds"], AGENT_CONFIG["research_timeout_seconds"])
        
        for _ in range(2): # Esperamos hasta 2 mensajes
            msg = await self.receive(timeout=timeout)
            if not msg:
                break # Timeout ocurrió
            
            sender_jid = str(msg.sender).split('/')[0] # Normalizar JID
            
            if sender_jid == AGENT_CONFIG["estimator_jid"]:
                if msg.metadata.get("performative") == "inform":
                    ml_estimate = json.loads(msg.body)
                    logger.info(f"Respuesta ML recibida para '{self.agent.get('story_title')}' {ml_estimate}")
                else:
                    logger.error("Se recibió una falla del Agente Estimador.")
                    self.agent.set("error_message", "Falla en la estimación de ML.")
                    self.set_next_state(AgentState.HANDLE_FAILURE.value)
                    return

            elif sender_jid == AGENT_CONFIG["researcher_jid"]:
                research_findings = json.loads(msg.body)
                logger.info(f"Hallazgos de investigación recibidos para '{self.agent.get('story_title')}' {research_findings}")

        # Verificar resultados
        if not ml_estimate:
            logger.error(f"No se recibió respuesta del Agente Estimador para '{self.agent.get('story_title')}'.")
            self.agent.set("error_message", "Timeout esperando al Agente Estimador.")
            self.set_next_state(AgentState.HANDLE_FAILURE.value)
            return
            
        if not research_findings:
            logger.warning("No se recibió respuesta del Agente Investigador. Continuando sin investigación.")
            research_findings = {"info": "No se realizó investigación externa."}

        self.agent.set("ml_estimate", ml_estimate)
        self.agent.set("research_findings", research_findings)
        self.set_next_state(AgentState.GENERATE_PLAN.value)


class GeneratePlanWithGeminiState(State):
    async def run(self) -> None:
        title = self.agent.get('story_title')
        logger.info(f"Generando plan técnico con LLM para '{title}'")

        story_data = self.agent.get('story_data')
        ml_estimate = self.agent.get('ml_estimate')
        research_findings = self.agent.get('research_findings')

        prompt = build_technical_plan_prompt(story_data, ml_estimate, research_findings)

        try:
            model = genai.GenerativeModel(AGENT_CONFIG["gemini_model"])
            generation_config = genai.types.GenerationConfig(response_mime_type="application/json")

            response = await model.generate_content_async(prompt, generation_config=generation_config)
            final_plan = json.loads(response.text)
            self.agent.set("final_plan", final_plan)

            logger.info(f"Plan técnico generado exitosamente para '{title}'")
            self.set_next_state(AgentState.FINALIZE.value)

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Fallo al decodificar JSON de la respuesta del LLM: {e}")
            logger.debug(f"Respuesta completa: {response.text}")
            self.agent.set("error_message", "Falla en la generación del plan: respuesta no es un JSON válido.")
            self.set_next_state(AgentState.HANDLE_FAILURE.value)

        except Exception as e:
            logger.error(f"Error inesperado al generar plan con LLM: {e}")
            self.agent.set("error_message", f"Falla en la generación del plan con LLM: {e}")
            self.set_next_state(AgentState.HANDLE_FAILURE.value)


class FinalizeState(State): 
    async def run(self) -> None:
        title = self.agent.get('story_title')
        logger.info(f"Plan técnico final para '{title}' enviado al solicitante.")
        msg = spade.message.Message(
            to=self.agent.get("original_sender"),
            body=json.dumps(self.agent.get("final_plan")),
            metadata={"performative": "inform"},
            thread=self.agent.get("thread_id")
        )
        await self.send(msg)
        self.set_next_state(AgentState.RECEIVE_STORY.value) # Listo para el siguiente ciclo

class HandleFailureState(State):
    async def run(self) -> None:
        error_msg = self.agent.get('error_message', 'Error desconocido')
        title = self.agent.get('story_title', 'Historia desconocida')
        logger.error(f"Gestionando fallo para '{title}'. Error: {error_msg}")
        
        failure_response = {
            "error": True,
            "message": error_msg,
            "story_title": title
        }
        
        msg = spade.message.Message(
            to=self.agent.get("original_sender"),
            body=json.dumps(failure_response),
            metadata={"performative": "failure"},
            thread=self.agent.get("thread_id")
        )
        await self.send(msg)
        self.set_next_state(AgentState.RECEIVE_STORY.value) # Listo para el siguiente ciclo