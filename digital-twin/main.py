import asyncio
import time
from estimator_agent import EstimatorAgent
from researcher_agent import ResearcherAgent
from reasoner_agent import ReasonerAgent
from planner_agent import PlannerAgent

XMPP_SERVER = "localhost"

async def main():
    """
    Función principal para instanciar y arrancar todos los agentes del sistema.
    """
    print("Iniciando el sistema de Gemelo Digital de Estimación...")

    # Crear instancias de los agentes
    # Se usan contraseñas dummy ya que es un entorno local.
    estimator = EstimatorAgent(f"estimator@{XMPP_SERVER}", "pass")
    reasoner = ReasonerAgent(f"reasoner@{XMPP_SERVER}", "pass")
    researcher = ResearcherAgent(f"researcher@{XMPP_SERVER}", "pass", "input/tech_stack.json")
    planner = PlannerAgent(f"planner@{XMPP_SERVER}", "pass", "input/stories_batch.json")
    
    # Iniciar los agentes
    await estimator.start(auto_register=True)
    await researcher.start(auto_register=True)
    await reasoner.start(auto_register=True)
    await planner.start(auto_register=True)

    print("Todos los agentes han sido iniciados. El Agente Planificador está comenzando el proceso.")
    
    # Mantener el script corriendo hasta que el planificador termine
    while planner.is_alive():
        try:
            await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Detención solicitada por el usuario.")
            break
    
    # Detener todos los agentes
    print("El Agente Planificador ha terminado. Deteniendo todos los agentes...")
    await estimator.stop()
    await researcher.stop()
    await reasoner.stop()
    
    print("Sistema detenido. ¡Hasta luego!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
