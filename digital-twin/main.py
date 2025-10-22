import asyncio
import argparse
from estimator.estimator_agent import EstimatorAgent
from researcher.researcher_agent import ResearcherAgent
from reasoner.reasoner_agent import ReasonerAgent
from planner.planner_agent import PlannerAgent
from web.agente_web import WebAgent
from config import XMPP_SERVER

async def main():
    """
    Función principal para instanciar y arrancar todos los agentes del sistema.
    """
    print("Iniciando el sistema de Gemelo Digital de Estimación...")

    # Crear instancias de los agentes
    estimator = EstimatorAgent(f"estimator@{XMPP_SERVER}", "pass")
    planner = PlannerAgent(f"planner@{XMPP_SERVER}", "pass")
    researcher = ResearcherAgent(f"researcher@{XMPP_SERVER}", "pass")
    reasoner = ReasonerAgent(f"reasoner@{XMPP_SERVER}", "pass")
    planner = PlannerAgent(f"planner@{XMPP_SERVER}", "pass")
    webAgent = WebAgent(f"webagent@{XMPP_SERVER}", "pass")
    
    print("Arrancando agentes de forma concurrente...")
    start_tasks = [
        researcher.start(auto_register=True),
        estimator.start(auto_register=True),
        reasoner.start(auto_register=True),
        planner.start(auto_register=True),
    ]
    await asyncio.gather(*start_tasks)
    await webAgent.start(auto_register=True)

    await asyncio.sleep(2)

    print("\n✅ Sistema listo. El Planificador está esperando lotes de trabajo.")
    print("El Emisor ha enviado un lote para su procesamiento.")
    print("Presiona Ctrl+C para detener todos los agentes.")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nDetención solicitada por el usuario.")
    finally:
        print("Deteniendo todos los agentes de forma concurrente...")
        stop_tasks = [
            estimator.stop(),
            researcher.stop(),
            reasoner.stop(),
            planner.stop(),
            webAgent.stop() # Asegúrate de que el webAgent también se detiene
        ]
        await asyncio.gather(*stop_tasks)
    
    print("Sistema detenido. ¡Hasta luego!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistema de Gemelo Digital de Estimación")
    try:
        asyncio.run(main())
    except KeyboardInterrupt as e:
        print(f"Feliz detención")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")    