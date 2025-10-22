# Digital Twin - Generador de Planes Técnicos

Este proyecto es una aplicación FastAPI que actúa como un "gemelo digital" de un equipo de ingeniería. Su función principal es recibir una historia de usuario en formato Gherkin y generar un plan técnico detallado para su implementación, utilizando una combinación de modelos de Machine Learning y un Modelo de Lenguaje Grande (LLM).

## Arquitectura

El sistema está orquestado por **LangGraph**, que define un flujo de trabajo claro y explícito. Cuando se recibe una solicitud, el grafo ejecuta los siguientes pasos en secuencia:

1.  **Investigación (ResearchService)**: Realiza una búsqueda web para recopilar contexto técnico relevante sobre las palabras clave y el título de la historia de usuario.
2.  **Predicción (PredictionService)**: Utiliza un modelo de Machine Learning (un `HistGradientBoostingRegressor` entrenado) para estimar el esfuerzo y el tiempo requeridos para la tarea, basándose en la descripción de la historia.
3.  **Planificación (LLMPlanGenerator)**: Alimenta al LLM (Gemini-Pro de Google) con la historia de usuario, la estimación del ML y los resultados de la investigación. El LLM, actuando como un Tech Lead, genera un plan de acción detallado, desglosado en tareas, y lo devuelve en un formato JSON estructurado gracias a `JsonOutputParser` de LangChain.

El uso de LangGraph permite una arquitectura modular y fácil de extender, donde cada paso es un nodo independiente en el grafo.

## Requisitos

- Python 3.8+
- Una clave de API de Google para el modelo Gemini (ver configuración).

## 1. Instalación

Clona el repositorio y navega al directorio del proyecto. Se recomienda crear un entorno virtual.

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

Instala las dependencias necesarias:

```bash
pip install -r requirements.txt
```

## 2. Configuración

La aplicación requiere una clave de API de Google para funcionar. Crea un archivo `.env` en el directorio raíz `digital-twin/` y añade tu clave:

```
# digital-twin/.env
GOOGLE_API_KEY="tu_clave_de_api_aqui"
```

## 3. Ejecutar la Aplicación

Una vez instaladas las dependencias y configurada la clave de API, puedes iniciar el servidor FastAPI con Uvicorn:

```bash
cd digital-twin
uvicorn main:app --reload
```

El servidor estará disponible en `http://127.0.0.1:8000`.

## 4. Uso del Endpoint

Puedes enviar una historia de usuario al endpoint `/generate_plan/` a través de una solicitud POST. Aquí tienes un ejemplo usando `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/generate_plan/" \
-H "Content-Type: application/json" \
-d '{
  "story_data": {
    "id": "STORY-006",
    "title": "Notificación en tiempo real al recibir mensaje",
    "gherkin": "Feature: Notificaciones en tiempo real\n  Scenario: El usuario recibe un nuevo mensaje directo\n    Given el usuario tiene sesión iniciada en la aplicación\n    And está en cualquier sección del sistema\n    When otro usuario le envía un mensaje\n    Then el sistema muestra una notificación en tiempo real con el remitente y el contenido del mensaje"
  }
}'
```

La API responderá con un plan técnico detallado en formato JSON, generado por el LLM.

## 5. Ejecutar las Pruebas

El proyecto incluye pruebas unitarias para verificar la correcta funcionalidad del endpoint y la integración de los componentes. Para ejecutarlas, primero instala las dependencias de desarrollo:

```bash
pip install pytest httpx
```

Luego, desde el directorio `digital-twin/`, ejecuta `pytest`:

```bash
pytest
```

Las pruebas utilizan mocks para simular las respuestas de los servicios externos (LLM, ML, Research), garantizando ejecuciones rápidas y predecibles sin coste de API.
