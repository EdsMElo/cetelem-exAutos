import os
import logging
import sys
from chromadb.config import Settings

# Configurações globais
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
VECTOR_STORE_DIR = "vector_stores"

# Configuração de logging melhorada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s',
    stream=sys.stdout
)

def get_logger(name):
    return logging.getLogger(name)

# Configurações do Chroma
CHROMA_SETTINGS = Settings(
    anonymized_telemetry=False
)

# Certifique-se de que o diretório de armazenamento de vetores existe
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)