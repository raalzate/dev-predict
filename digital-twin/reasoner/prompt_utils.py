import json

def build_technical_plan_prompt(story_data: dict, ml_estimate: dict, research_findings: dict) -> str:
    """
    Genera el prompt para el modelo Gemini a partir de los datos de la historia,
    la estimación ML y la investigación adicional. Retorna un string listo para usar.
    """
    return f"""
Actúa como un Tech Lead experto en ingeniería de software.
Tu misión es crear un **plan técnico realizable y concreto** a partir de una historia de usuario,
respetando un presupuesto fijo de horas proveniente del modelo de estimación de ML.

### Entradas
**Historia de Usuario:**
{json.dumps(story_data, indent=2, ensure_ascii=False)}

**Estimación Fija (Presupuesto ML):**
{json.dumps(ml_estimate, indent=2)}

**Investigación Adicional (Contexto):**
{json.dumps(research_findings, indent=2, ensure_ascii=False)}

---

### Instrucciones

1. **Acepta** la estimación ML como el presupuesto final (`budget_hours`).
2. **Determina** la complejidad general (`overall_complexity`) en una de estas categorías:
   "Low", "Medium" o "High".
3. **Crea** un objeto JSON dentro de una lista `[ ... ]` con **exactamente** la siguiente estructura:

[
  {{
    "story_id": "<usa el campo id o genera uno con prefijo STORY->>",
    "story_title": "<título de la historia>",
    "ml_estimate_accepted": true,
    "effort": <usa el valor numérico del ML>,
    "time": <usa el valor numérico del ML>,
    "overall_complexity": "<Low | Medium | High>",
    "action_plan": {{
       "description": "<resumen general del trabajo dentro del presupuesto>",
       "tasks": [
          {{
            "task_name": "1. <nombre de la tarea>",
            "estimated_hours": <número>,
            "details": "<detalle claro y técnico>"
          }}
       ]
    }},
    "key_considerations": [
       "<consideración 1>",
       "<consideración 2>"
    ],
    "risks_and_dependencies": {{
        "dependencies": ["<dependencia 1>", "<dependencia 2>"],
        "risks": ["<riesgo 1>", "<riesgo 2>"]
    }}
  }}
]

4. La respuesta **debe ser estrictamente JSON válido** (sin texto adicional ni explicación).
5. El total de horas **no debe exceder** el valor de `budget_hours`.

Recuerda: sé conciso, técnico y prioriza lo realizable dentro del presupuesto.
    """
