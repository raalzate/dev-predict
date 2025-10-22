import spade
from spade.behaviour import CyclicBehaviour
import json
import uuid
import logging

logger = logging.getLogger("PlannerAgent")

class PlannerAgent(spade.agent.Agent):
    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.stories = []
        self.results = []

    class ReceiveBatchAndProcessBehav(CyclicBehaviour): 
        
        async def run(self):            
            msg = await self.receive(timeout=None) 
            
            if msg:
                sender_jid = str(msg.sender)
                logger.info(f"[Planner] Recibido mensaje de: {sender_jid}")

                reply = msg.make_reply()

                try:
                    # Primero, decodificamos el JSON a un objeto de Python
                    data = json.loads(msg.body)
                    self.agent.results = []

                    if isinstance(data, list):
                        if not all(isinstance(item, dict) for item in data):
                            reply.body = "Error: La lista JSON debe contener únicamente objetos {...}, no strings u otros tipos."
                            reply.metadata = {"performative": "failure"}
                            await self.send(reply)
                            return
                        
                        self.agent.stories = data
                        reply.body = f"Lote de {len(self.agent.stories)} historias recibido. Iniciando procesamiento..."
                        reply.metadata = {"performative": "confirm"}
                        await self.send(reply)

                    elif isinstance(data, dict):
                        self.agent.stories = [data]
                        reply.body = "Historia individual recibida. Iniciando procesamiento..."
                        reply.metadata = {"performative": "confirm"}
                        await self.send(reply)
                    else:
                        reply.body = "Error: El formato del JSON debe ser una lista de historias [...] o un único objeto de historia {...}."
                        reply.metadata = {"performative": "failure"}
                        await self.send(reply)
                        return
                    # -----------------------------------------------------------------

                except json.JSONDecodeError:
                    reply.body = "Error: El mensaje recibido no contiene un JSON válido."
                    reply.metadata = {"performative": "failure"}
                    await self.send(reply)
                    return
                
                for story in self.agent.stories:
                    thread_id = str(uuid.uuid4())
                    request_msg = spade.message.Message(to="reasoner@localhost", body=json.dumps(story), metadata={"performative": "request"}, thread=thread_id)
                    await self.send(request_msg)
                    response = await self.receive(timeout=1200)
                    if response:
                        self.agent.results.append(json.loads(response.body))
                    else:
                        self.agent.results.append({"error": True, "message": "Timeout del Planificador", "story_title": story.get('title', 'N/A')})
                
                
                final_reply = msg.make_reply()
                final_reply.body = json.dumps(self.agent.results)
                final_reply.metadata = {"performative": "result"}
                
                logger.info(f"[Planner] Proceso completado. Enviando reporte final a {sender_jid}.")
                await self.send(final_reply)

        

    async def setup(self):
        logger.info(f"[PlannerAgent] Agente planificador '{str(self.jid)}' iniciado y listo para recibir lotes.")
        self.add_behaviour(self.ReceiveBatchAndProcessBehav())