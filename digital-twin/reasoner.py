import logging
import json
import os
from dotenv import load_dotenv
from typing import List, Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

# Cargar variables de entorno desde .env
load_dotenv()

logger = logging.getLogger(__name__)

# --- Definición de la estructura de salida con Pydantic ---
# Esto ayuda a LangChain a generar el formato JSON correcto y a validarlo.

class Task(BaseModel):
    task_name: str = Field(description="Nombre de la tarea, comenzando con un número. Ej: '1. <nombre>'")
    estimated_hours: float = Field(description="Horas estimadas para la tarea")
    details: str = Field(description="Detalle claro y técnico de lo que implica la tarea")

class ActionPlan(BaseModel):
    description: str = Field(description="Resumen general del trabajo a realizar dentro del presupuesto de horas estimado.")
    tasks: List[Task]

class RisksAndDependencies(BaseModel):
    dependencies: List[str] = Field(description="Lista de dependencias externas o de otros equipos.")
    risks: List[str] = Field(description="Lista de riesgos potenciales del proyecto.")

class TechnicalPlan(BaseModel):
    story_id: str = Field(description="ID de la historia de usuario, usando el campo 'id' de la entrada o generando uno nuevo con prefijo 'STORY-'.")
    story_title: str = Field(description="Título de la historia de usuario.")
    ml_estimate_accepted: bool = Field(description="Siempre `true`, indicando que la estimación del ML es aceptada.", default=True)
    effort: float = Field(description="El valor numérico de 'effort' de la estimación ML.")
    time: float = Field(description="El valor numérico de 'time' (en horas) de la estimación ML.")
    overall_complexity: Literal["Low", "Medium", "High"] = Field(description="Complejidad general del proyecto.")
    action_plan: ActionPlan
    key_considerations: List[str] = Field(description="Puntos clave a tener en cuenta durante la implementación.")
    risks_and_dependencies: RisksAndDependencies

def build_prompt_text(story_data: str, ml_estimate: str, research_findings: str) -> str:
    """
    Genera el texto del prompt para el modelo.
    Los detalles de la estructura JSON serán añadidos por el parser de LangChain.
    """
    return f"""
Actúa como un Tech Lead experto en ingeniería de software.
Tu misión es crear un **plan técnico realizable y concreto** a partir de una historia de usuario,
respetando un presupuesto fijo de horas proveniente del modelo de estimación de ML.

### Entradas
**Historia de Usuario:**
{story_data}

**Estimación Fija (Presupuesto ML):**
{ml_estimate}

**Investigación Adicional (Contexto):**
{research_findings}

---

### Instrucciones

1.  **Analiza** toda la información de entrada para tomar decisiones informadas.
2.  **Acepta** la estimación ML como el presupuesto final (`budget_hours`). El total de horas de las tareas no debe exceder este valor.
3.  **Determina** la complejidad general (`overall_complexity`).
4.  **Desglosa** el trabajo en tareas técnicas específicas, claras y accionables.
5.  **Identifica** consideraciones clave, dependencias y riesgos basados en tu análisis.
6.  **Genera** la respuesta JSON con un único plan técnico dentro de una lista.
"""

class LLMPlanGenerator:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("La variable de entorno GOOGLE_API_KEY no está configurada.")
        
        # El parser se instancia con el modelo Pydantic que define la estructura de salida.
        # LangChain usará esto para generar instrucciones de formato y para parsear la salida.
        self.parser = JsonOutputParser(pydantic_object=List[TechnicalPlan])

        # Se configura el prompt template, inyectando las instrucciones de formato del parser.
        prompt_template = ChatPromptTemplate.from_template(
            template="{prompt}\n\n{format_instructions}",
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        # Se configura el LLM. `temperature=0.2` para un equilibrio entre creatividad y consistencia.
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key, temperature=0.2)
        
        # Se construye la cadena de LangChain.
        self.chain = prompt_template | self.llm | self.parser
        logger.info("LLMPlanGenerator inicializado con LangChain, Gemini-Pro y JsonOutputParser.")

    def generate_plan(self, story_data: dict, ml_estimate: dict, research_findings: dict) -> List[dict]:
        """
        Genera un plan de implementación técnico detallado utilizando el LLM con LangChain.
        """
        prompt = build_prompt_text(
            story_data=json.dumps(story_data, indent=2, ensure_ascii=False),
            ml_estimate=json.dumps(ml_estimate, indent=2),
            research_findings=json.dumps(research_findings, indent=2, ensure_ascii=False)
        )
        
        try:
            # Se invoca la cadena con el prompt. El parser se encarga de devolver un dict/list.
            technical_plan = self.chain.invoke({"prompt": prompt})
            return technical_plan
        except Exception as e:
            logger.error(f"Error inesperado al generar el plan con LangChain: {e}")
            # Aquí podrías añadir lógica de reintentos o manejo de errores más específico.
            raise
