import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from config import XMPP_SERVER
import logging

logger = logging.getLogger("WebAgent")

class WebAgent(Agent):
    async def unsubscribe_all(self):
        """Desuscribe de todos los agentes conocidos."""
        targets = [
            f"estimator@{XMPP_SERVER}",
            f"planner@{XMPP_SERVER}",
            f"researcher@{XMPP_SERVER}",
        ]
        for jid in targets:
            try:
                await self.presence.unsubscribe(jid)
                logger.info(f"Desuscrito de {jid}")
            except Exception as e:
                logger.warning(f"No se pudo desuscribir de {jid}: {e}")

    class PresenceBehaviour(OneShotBehaviour):
        async def run(self):
            logger.info("Enviando solicitudes de presencia...")
            self.agent.presence.subscribe(f"estimator@{XMPP_SERVER}")
            self.agent.presence.subscribe(f"planner@{XMPP_SERVER}")
            self.agent.presence.subscribe(f"researcher@{XMPP_SERVER}")
            logger.info("Suscripciones de presencia enviadas")

    class SampleBehaviour(CyclicBehaviour):
        async def run(self):
            logger.info("Sample behaviour running")
            await asyncio.sleep(5)

    async def setup(self):
        logger.info(f"Agent {self.jid} iniciado")

        self.add_behaviour(self.PresenceBehaviour())
        # self.add_behaviour(self.SampleBehaviour())

        # Iniciar el servidor web
        await self.web.start(hostname="127.0.0.1", port="10000", templates_path="static/templates")
        logger.info("Servidor web iniciado en http://127.0.0.1:10000/spade")

    async def stop(self):
        """Intercepta la desconexión para limpiar correctamente las suscripciones."""
        logger.info(f"Deteniendo agente {self.jid}...")
        await self.unsubscribe_all()
        await super().stop()
        logger.info(f"Agente {self.jid} detenido y desuscrito correctamente.")
