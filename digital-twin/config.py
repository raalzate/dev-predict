import os
from dotenv import load_dotenv

# Carga las variables de entorno desde un archivo .env
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")
