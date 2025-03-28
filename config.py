import os
import logging
import sys
from chromadb.config import Settings

# Configurações globais
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
VECTOR_STORE_DIR = "vector_stores"
DEBUG_ENABLED = True  # Nova configuração para controle de debug

# Configuração de logging melhorada
class CustomFilter(logging.Filter):
    def filter(self, record):
        return DEBUG_ENABLED or record.levelno >= logging.ERROR

logging.basicConfig(
    level=logging.DEBUG,  
    format='%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s',
    stream=sys.stdout,
    force=True  
)

# Configurar loggers específicos
for logger_name in ['werkzeug', 'selenium', 'urllib3']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)  

def get_logger(name):
    logger = logging.getLogger(name)
    logger.addFilter(CustomFilter())
    return logger

# Configurações do Chroma
CHROMA_SETTINGS = Settings(
    anonymized_telemetry=False
)

# Certifique-se de que o diretório de armazenamento de vetores existe
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)