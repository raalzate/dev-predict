import spade
from spade.behaviour import OneShotBehaviour
from spade.template import Template
import json
import uuid

class PlannerAgent(spade.agent.Agent):
    """
    Agente que actúa como "Project Manager".
    Carga un lote de historias, delega su estimación de forma secuencial y consolida los resultados.
    """
    def __init__(self, jid, password, stories_file):
        super().__init__(jid, password)
        self.stories_file = stories_file
        self.stories = []
        self.results = []

    class ProcessBatchSequentiallyBehav(OneShotBehaviour):
        
        def load_stories(self):
            try:
                with open(self.agent.stories_file, 'r', encoding='utf-8') as f:
                    self.agent.stories = json.load(f)
                print(f"[Planner] Lote de {len(self.agent.stories)} historias cargado. Iniciando proceso.")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"[Planner] ERROR: No se pudo cargar el archivo de historias: {e}")
                self.agent.stories = []

        async def run(self):
            self.load_stories()
            if not self.agent.stories:
                print("[Planner] No hay historias para procesar. Deteniendo.")
                await self.agent.stop()
                return

            # **CORRECCIÓN CLAVE:** Procesar una historia a la vez, esperando la respuesta.
            for story in self.agent.stories:
                thread_id = str(uuid.uuid4())
                title = story.get('title', 'N/A')
                print(f"[Planner] Enviando '{title}' al Razonador (Thread: {thread_id}).")

                # Enviar la solicitud
                msg = spade.message.Message(
                    to="reasoner@localhost",
                    body=json.dumps(story),
                    metadata={"performative": "request"},
                    thread=thread_id
                )
                await self.send(msg)

                # Esperar la respuesta específica para este hilo de conversación
                template = Template(thread=thread_id)
                response = await self.receive(timeout=60) # Aumentado el timeout para Gemini

                if response:
                    print(f"[Planner] Recibida estimación final para '{title}'.")
                    self.agent.results.append(json.loads(response.body))
                else:
                    print(f"[Planner] ERROR: Timeout esperando la respuesta para '{title}'.")
                    self.agent.results.append({"error": True, "message": "Timeout del Planificador", "story_title": title})
            
            self.show_final_report()
            print("\n[Planner] Proceso completado. Deteniendo.")
            await self.agent.stop()

        def show_final_report(self):
            print("\n" + "="*50)
            print("INFORME FINAL DE ESTIMACIÓN DEL LOTE")
            print("="*50)
            total_effort = 0
            total_time = 0

            for i, result in enumerate(self.agent.results):
                story_title = self.agent.stories[i].get('title', 'Desconocido')
                print(f"\n--- Historia: {story_title} ---")
                
                if result and not result.get("error"):
                    effort = result.get('effort_refined', 0)
                    time = result.get('time_estimated', 0)
                    complexity = result.get('complexity', 'N/A')
                    justification = result.get('justification', 'N/A')
                    
                    effort = float(effort) if effort is not None else 0
                    time = float(time) if time is not None else 0
                    total_effort += effort
                    total_time += time
                    
                    print(f"  - Esfuerzo Refinado: {effort:.2f} puntos")
                    print(f"  - Tiempo Estimado: {time:.2f} horas")
                    print(f"  - Complejidad: {complexity}")
                    print(f"  - Justificación: {justification}")
                else:
                    message = result.get('message', 'Error desconocido') if result else "Sin respuesta"
                    print(f"  - ESTADO: FALLIDO")
                    print(f"  - Razón: {message}")
            
            print("\n" + "="*50)
            print("TOTALES DEL LOTE")
            print("="*50)
            print(f"Esfuerzo Total Estimado: {total_effort:.2f} puntos")
            print(f"Tiempo Total Estimado: {total_time:.2f} horas")
            print("="*50)

    async def setup(self):
        print(f"[Planner] Agente planificador '{str(self.jid)}' iniciado.")
        self.add_behaviour(self.ProcessBatchSequentiallyBehav())

