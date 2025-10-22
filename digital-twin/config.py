import logging
import os
from enum import Enum
from dotenv import load_dotenv
import google.generativeai as genai

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- Carga de variables de entorno ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
XMPP_SERVER = os.getenv("XMPP_SERVER", "localhost" )
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")


if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logging.getLogger("CONFIG").error("La variable de entorno GEMINI_API_KEY no fue encontrada.")

AGENT_CONFIG = {
    "estimator_jid": f"estimator@{XMPP_SERVER}",
    "researcher_jid": f"researcher@{XMPP_SERVER}",
    "gemini_model": "gemini-2.5-flash",
    "ml_timeout_seconds": 80,
    "research_timeout_seconds": 1000,
    "initial_receive_timeout": 1000,
}

# --- Definición de Estados ---
class AgentState(Enum):
    RECEIVE_STORY = "RECEIVE_STORY"
    REQUEST_DATA = "REQUEST_DATA"
    WAIT_FOR_DATA = "WAIT_FOR_DATA"
    GENERATE_PLAN = "GENERATE_PLAN"
    FINALIZE = "FINALIZE"
    HANDLE_FAILURE = "HANDLE_FAILURE"