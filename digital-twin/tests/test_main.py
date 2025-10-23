import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Mocks para los servicios ---
# Se crean mocks para evitar llamadas reales a los servicios durante los tests.

mock_prediction_service = MagicMock()
mock_prediction_service.predict.return_value = (5.0, 8.0) # (effort, time)

mock_research_service = AsyncMock()
mock_research_service.conduct_research.return_value = {"summary": "Investigación sobre WebSockets y notificaciones en tiempo real."}

mock_llm_plan_generator = MagicMock()
mock_llm_plan_generator.generate_plan.return_value = [
    {
        "story_id": "STORY-006",
        "story_title": "Notificación en tiempo real al recibir mensaje",
        "technical_plan": "..."
    }
]

# Aplicamos los mocks a nivel de módulo para que se usen en lugar de los reales.
# Esto se hace ANTES de importar 'app' para que la app se inicialice con los mocks.
with patch.dict(sys.modules, {
    'prediction': MagicMock(PredictionService=lambda **kwargs: mock_prediction_service),
    'research': MagicMock(ResearchService=lambda **kwargs: mock_research_service),
    'reasoner': MagicMock(LLMPlanGenerator=lambda **kwargs: mock_llm_plan_generator),
}):
    from main import app # La importación de la app se hace después de aplicar los mocks

# --- Datos de Prueba ---

STORY_DATA_INPUT = {
    "id": "STORY-006",
    "title": "Notificación en tiempo real al recibir mensaje",
    "gherkin": (
        "Feature: Notificaciones en tiempo real\n"
        "  Scenario: El usuario recibe un nuevo mensaje directo\n"
        "    Given el usuario tiene sesión iniciada en la aplicación\n"
        "    And está en cualquier sección del sistema\n"
        "    When otro usuario le envía un mensaje\n"
        "    Then el sistema muestra una notificación en tiempo real con el remitente y el contenido del mensaje"
    )
}

# --- Test Asíncrono con pytest ---

@pytest.mark.asyncio
async def test_generate_plan_endpoint():
    """
    Test para el endpoint /generate_plan/.
    Verifica que el endpoint procesa la solicitud, invoca el grafo y devuelve el plan técnico.
    """
    # Usamos AsyncClient de httpx para hacer peticiones a nuestra app FastAPI.
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Realizamos la petición POST al endpoint.
        response = await client.post("/generate_plan/", json={"story_data": STORY_DATA_INPUT})
    
    # --- Verificaciones ---
    
    # 1. Verificar que la respuesta HTTP es exitosa.
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    # 2. Verificar que el contenido de la respuesta es el esperado (el plan del mock).
    response_data = response.json()
    expected_plan = mock_llm_plan_generator.generate_plan.return_value
    assert response_data == expected_plan, "El plan devuelto no coincide con el mock."
    
    # 3. Verificar que los servicios fueron llamados correctamente.
    # El grafo de LangGraph llama a los métodos de los servicios.
    mock_research_service.conduct_research.assert_called_once()
    mock_prediction_service.predict.assert_called_once_with(STORY_DATA_INPUT)
    mock_llm_plan_generator.generate_plan.assert_called_once()
