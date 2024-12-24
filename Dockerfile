# Use uma imagem base do Python
FROM python:3.12.5-slim-bullseye

WORKDIR /app

# Instalar dependências do sistema necessárias
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copiar os arquivos do projeto
COPY requirements.txt .
COPY *.py .
COPY templates templates/
COPY static static/

# Configurar o ambiente
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=$OLLAMA_HOST
ENV PATH="/usr/local/bin:$PATH"
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Criar e ativar ambiente virtual
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Verificar a instalação básica
RUN python --version && \
    pip list

# Criar diretório para downloads e dar permissões apropriadas
RUN mkdir -p /app/downloads && \
    chmod -R 777 /app/downloads

# Expor a porta da aplicação
EXPOSE 7860

# Comando para executar a aplicação
CMD ["python", "app.py"]