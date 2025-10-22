import spade
from spade.behaviour import FSMBehaviour
import logging

# Importaciones desde nuestros propios módulos
from reasoner.states import (
    ReceiveStoryState,
    RequestDataInParallelState,
    WaitForDataState,
    GeneratePlanWithGeminiState,
    FinalizeState,
    HandleFailureState
)
from config import AgentState

logger = logging.getLogger("ReasonerAgent")

class ReasonerAgent(spade.agent.Agent):
    
    class ReasonerFSM(FSMBehaviour):
        async def on_start(self):
            logger.info("FSM iniciada. Esperando por una historia de usuario...")

        async def on_end(self):
            title = self.agent.get('story_title') or "una historia desconocida"
            logger.info(f"FSM ha completado un ciclo para la historia: {title}")
    
    async def setup(self):
        logger.info("Agente razonador iniciado. Creando FSM.")
        fsm = self.ReasonerFSM()

        # Añadir estados
        fsm.add_state(name=AgentState.RECEIVE_STORY.value, state=ReceiveStoryState(), initial=True)
        fsm.add_state(name=AgentState.REQUEST_DATA.value, state=RequestDataInParallelState())
        fsm.add_state(name=AgentState.WAIT_FOR_DATA.value, state=WaitForDataState())
        fsm.add_state(name=AgentState.GENERATE_PLAN.value, state=GeneratePlanWithGeminiState()) 
        fsm.add_state(name=AgentState.FINALIZE.value, state=FinalizeState()) 
        fsm.add_state(name=AgentState.HANDLE_FAILURE.value, state=HandleFailureState())

        # Añadir transiciones
        fsm.add_transition(source=AgentState.RECEIVE_STORY.value, dest=AgentState.REQUEST_DATA.value)
        fsm.add_transition(source=AgentState.REQUEST_DATA.value, dest=AgentState.WAIT_FOR_DATA.value)
        fsm.add_transition(source=AgentState.WAIT_FOR_DATA.value, dest=AgentState.GENERATE_PLAN.value)
        fsm.add_transition(source=AgentState.WAIT_FOR_DATA.value, dest=AgentState.HANDLE_FAILURE.value)
        fsm.add_transition(source=AgentState.GENERATE_PLAN.value, dest=AgentState.FINALIZE.value) 
        fsm.add_transition(source=AgentState.GENERATE_PLAN.value, dest=AgentState.HANDLE_FAILURE.value)
        fsm.add_transition(source=AgentState.FINALIZE.value, dest=AgentState.RECEIVE_STORY.value)
        fsm.add_transition(source=AgentState.HANDLE_FAILURE.value, dest=AgentState.RECEIVE_STORY.value)

        self.add_behaviour(fsm)