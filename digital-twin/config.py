import os
from dotenv import load_dotenv
import re
import pandas as pd

# Carga las variables de entorno desde un archivo .env
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

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