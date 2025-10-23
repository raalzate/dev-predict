import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import TypedDict, Dict, Any, List

from langgraph.graph import StateGraph, END

from prediction import PredictionService
from reasoner import LLMPlanGenerator
from research import ResearchService

app = FastAPI()

# --- Definición de la estructura de la solicitud ---
class PlanRequest(BaseModel):
    story_data: dict

# --- Inicialización de Servicios ---
# Estos servicios encapsulan la lógica de cada paso del proceso.
MODEL_PATH = 'model/effort_model.joblib'
TECH_STACK_FILE = 'model/tech_stack.json'

try:
    prediction_service = PredictionService(model_path=MODEL_PATH)
    research_service = ResearchService(tech_stack_file=TECH_STACK_FILE)
    llm_plan_generator = LLMPlanGenerator()
except Exception as e:
    raise RuntimeError(f"Error al inicializar los servicios: {e}")

# --- Definición del Estado del Grafo LangGraph ---
# El estado es un diccionario que se pasa entre los nodos del grafo.
class GraphState(TypedDict):
    story_data: Dict[str, Any]
    research_findings: Dict[str, Any]
    ml_estimate: Dict[str, Any]
    technical_plan: List[Dict[str, Any]]

# --- Definición de los Nodos del Grafo ---
# Cada nodo es una función que opera sobre el estado del grafo.

async def run_research(state: GraphState) -> Dict[str, Any]:
    """Nodo que ejecuta la investigación web basada en la historia de usuario."""
    print("--- Ejecutando Investigación ---")
    story_data = state['story_data']
    findings = await research_service.conduct_research(
        story_data.get("title", ""), 
        story_data.get("keywords", [])
    )
    return {"research_findings": findings}

def run_prediction(state: GraphState) -> Dict[str, Any]:
    """Nodo que ejecuta el modelo de predicción de ML."""
    print("--- Ejecutando Predicción ML ---")
    effort, time = prediction_service.predict(state['story_data'])
    ml_estimate = {"effort": effort, "time": time, "budget_hours": time}
    return {"ml_estimate": ml_estimate}

def generate_technical_plan(state: GraphState) -> Dict[str, Any]:
    """Nodo que genera el plan técnico final usando el LLM."""
    print("--- Generando Plan Técnico ---")
    plan = llm_plan_generator.generate_plan(
        state['story_data'],
        state['ml_estimate'],
        state['research_findings']
    )
    return {"technical_plan": plan}

# --- Construcción del Grafo con LangGraph ---

# Se define el grafo de estados.
workflow = StateGraph(GraphState)

# Se añaden los nodos al grafo.
workflow.add_node("research", run_research) 
workflow.add_node("prediction", run_prediction)
workflow.add_node("planner", generate_technical_plan)

# Se definen las transiciones (el orden de ejecución).
workflow.set_entry_point("research")
workflow.add_edge("research", "prediction")
workflow.add_edge("prediction", "planner")
workflow.add_edge("planner", END)

# Se compila el grafo en una aplicación ejecutable.
graph_app = workflow.compile()

# --- Endpoint de FastAPI ---

@app.post("/generate_plan/")
async def generate_plan_endpoint(request: PlanRequest):
    """
    Endpoint que recibe una historia de usuario e invoca el grafo de LangGraph
    para orquestar la generación del plan técnico completo.
    """
    initial_state = {"story_data": request.story_data}
    
    try:
        # Se invoca el grafo con el estado inicial.
        # LangGraph se encarga de ejecutar los nodos en el orden definido.
        final_state = await graph_app.ainvoke(initial_state)
        
        # Se devuelve el resultado final del grafo.
        return final_state.get("technical_plan")
        
    except Exception as e:
        # Manejo de errores durante la ejecución del grafo.
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado en el grafo: {str(e)}")

# --- Ejecución de la aplicación ---

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
