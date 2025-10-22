import spade
import re
import spacy
from spade.behaviour import CyclicBehaviour
import joblib
import json
import pandas as pd
import os
import logging

logger = logging.getLogger("EstimatorAgent")

NUMERICAL_FEATURES = [
    'gherkin_steps', 'gherkin_length', 'num_scenarios', 'num_technical_terms',
    'num_conditions', 'num_entities', 'num_roles',
    'has_frontend', 'has_backend', 'has_security', 'has_payment', 'has_crud',
    'has_reporting', 'has_integration', 'has_notification', 'has_devops_mlops',
    'has_accessibility', 'has_mobile', 'has_testing', 'has_error_handling',
    'has_ui_interaction', 'has_database_query', 'tech_java', 'tech_node',
    'tech_python', 'tech_frontend_framework', 'tech_database', 'tech_infra_cloud'
]

# ---------------------------------------------------------------------------
# La función `extract_features` es la misma, ya que el Pipeline la necesita
# para crear las columnas numéricas iniciales antes de vectorizar y escalar.
def extract_features(df: pd.DataFrame) -> (pd.DataFrame):
  
    df_featured = df.copy()

    df_featured['gherkin'] = df_featured['gherkin'].astype(str).fillna('')
    df_featured['title'] = df_featured['title'].astype(str).fillna('')
    df_featured['full_text'] = df_featured['title'] + " " + df_featured['gherkin']

    # --- Características Basadas en Categorías (Regex mejoradas con \b) ---
    keyword_categories = {
        'has_frontend': r'\b(?:frontend|UI|interfaz|CSS|React|Angular|Vue|diseño|vista|pantalla)\b',
        'has_backend': r'\b(?:backend|servidor|database|base de datos|bd|API|endpoint|SQL|servicios|microservicio|Java|NodeJS|NestJS|Python)\b',
        'has_security': r'\b(?:seguridad|security|JWT|OAuth|token|autenticación|contraseña|encriptar|CSRF|XSS)\b',
        'has_payment': r'\b(?:pago|payment|stripe|paypal|tarjeta de crédito|checkout|factura|compra)\b',
        'has_crud': r'\b(?:crear|añadir|guardar|editar|actualizar|modificar|eliminar|borrar|ver|listar|obtener)\b',
        'has_reporting': r'\b(?:reporte|dashboard|gráfico|exportar|CSV|PDF|Excel|analíticas|métricas)\b',
        'has_integration': r'\b(?:api externa|third-party|integración|webhook|sincronizar|CRM|ERP)\b',
        'has_notification': r'\b(?:notificación|email|correo|SMS|push|alerta|mensaje)\b',
        'has_devops_mlops': r'\b(?:CI/CD|pipeline|deploy|despliegue|Kubernetes|Docker|monitor|observabilidad|modelo|ML|IA|DevOps)\b',
        'has_accessibility': r'\b(?:accesibilidad|accessibility|WCAG|lector de pantalla|screen reader|ARIA)\b',
        'has_mobile': r'\b(?:móvil|app|push|biometría|offline|geolocalización|cámara|gesto)\b',
        'has_testing': r'\b(?:test|prueba|mock|verificar|validar|assertion|simula)\b',
        'has_error_handling': r'\b(?:error|excepción|exception|fallo|failure|validar|manejo de error)\b',
        'has_ui_interaction': r'\b(?:clic|seleccionar|navegar|click|select)\b',
        'has_database_query': r'\b(?:query|select|sql|database|base de datos|bd)\b'
    }
    for feature_name, pattern in keyword_categories.items():
        df_featured[feature_name] = df_featured['full_text'].str.contains(pattern, case=False, regex=True, na=False).astype(int)

    tech_stack_keywords = {
        'tech_java': r'\b(?:java|spring|maven|gradle|JPA|hibernate)\b',
        'tech_node': r'\b(?:node\.?js|nestjs|express|npm|yarn)\b',
        'tech_python': r'\b(?:python|django|flask|fastapi|pip)\b',
        'tech_frontend_framework': r'\b(?:react|angular|vue|svelte)\b',
        'tech_database': r'\b(?:sql|mysql|postgres|mongodb|redis|base de datos|database)\b',
        'tech_infra_cloud': r'\b(?:aws|azure|gcp|docker|kubernetes|terraform|S3)\b'
    }
    for tech_name, pattern in tech_stack_keywords.items():
        df_featured[tech_name] = df_featured['full_text'].str.contains(pattern, case=False, regex=True, na=False).astype(int)

    # --- Características Cuantitativas ---
    gherkin_keywords = [r'\bGiven\b', r'\bWhen\b', r'\bThen\b', r'\bAnd\b', r'\bDado\b', r'\bCuando\b', r'\bEntonces\b', r'\bY\b']
    df_featured['gherkin_steps'] = df_featured['gherkin'].apply(lambda x: sum(len(re.findall(word, x, re.IGNORECASE)) for word in gherkin_keywords))
    df_featured['gherkin_length'] = df_featured['gherkin'].str.len()
    df_featured['num_scenarios'] = df_featured['gherkin'].str.count(r'\b(Scenario|Escenario)\b', re.IGNORECASE)
    df_featured['num_conditions'] = df_featured['gherkin'].str.lower().str.count(r'\b(if|when|si)\b')

    # Lista de todas las características numéricas creadas
    numerical_features = list(keyword_categories.keys()) + \
                         list(tech_stack_keywords.keys()) + \
                         ['gherkin_steps', 'gherkin_length', 'num_scenarios', 'num_conditions']

    for col in numerical_features:
        df_featured[col] = pd.to_numeric(df_featured[col], errors='coerce').fillna(0).astype(float)

    return df_featured

# ---------------------------------------------------------------------------

class PredictionService:
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"El archivo del pipeline del modelo no se encontró en: {model_path}")
        self.pipeline = joblib.load(model_path)
        
        try:
            self.nlp = spacy.load('es_core_news_sm')
        except OSError:
            print("Modelo 'es_core_news_sm' no encontrado. Por favor, ejecute: python -m spacy download es_core_news_sm")
            exit()
        logger.info("[PredictionService] Pipeline de predicción cargado correctamente.")

    def lemmatize_text(self, text: str) -> str:
        """
        Convierte un texto en una cadena de lemas usando el modelo nlp de la instancia.
        """
        doc = self.nlp(text.lower())
        return " ".join([token.lemma_ for token in doc if not token.is_stop and not token.is_punct])

    def predict(self, story_data: dict) -> tuple[float, float]:
        single_story_df = pd.DataFrame([story_data])
        df_featured = extract_features(single_story_df)

        df_featured['full_text_lemmatized'] = df_featured['full_text'].apply(self.lemmatize_text)        
        prediction = self.pipeline.predict(df_featured)
        
        logger.info(f"[PredictionService] Predicción cruda del modelo: {prediction}")
        
        effort, time = prediction[0]
        return effort, time

# ---------------------------------------------------------------------------

class EstimatorAgent(spade.agent.Agent):
    """
    Agente que recibe solicitudes de estimación y responde con predicciones.
    """
    MODEL_PATH = 'estimator/model/effort_model.joblib' 
    
    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.prediction_service = None

    class EstimationBehav(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10) 
            if msg:
                story_data = json.loads(msg.body)
                title = story_data.get('title', 'N/A')
                logger.info(f"[Estimator] Recibida solicitud para: '{title}'")

                try:
                    # La lógica compleja ahora está en el servicio de predicción
                    effort, time = self.agent.prediction_service.predict(story_data)
                    
                    logger.info(f"[Estimator] Predicción para '{title}': Esfuerzo={effort:.1f}, Tiempo={time:.1f}h")

                    # Enviar respuesta
                    reply = spade.message.Message(
                        to=str(msg.sender),
                        body=json.dumps({"effort": round(effort, 2), "time": round(time, 2)}),
                        metadata={"performative": "inform"},
                        thread=msg.thread
                    )
                    await self.send(reply)

                except Exception as e:
                    print(f"[Estimator] Error durante la predicción: {e}", e)
                    error_reply = spade.message.Message(
                        to=str(msg.sender),
                        body=json.dumps({"error": f"Error interno del estimador: {e}"}),
                        metadata={"performative": "failure"},
                        thread=msg.thread
                    )
                    await self.send(error_reply)

    async def setup(self):
        logger.info(f"[EstimatorAgent] Agente estimador '{str(self.jid)}' iniciado.")
        try:
            self.prediction_service = PredictionService(self.MODEL_PATH)
            self.add_behaviour(self.EstimationBehav())
        except FileNotFoundError as e:
            logger.info(f"[Estimator] ERROR CRÍTICO: {e}")
            logger.info("[Estimator] Por favor, asegúrate de que el modelo ha sido entrenado y guardado correctamente.")
            await self.stop()