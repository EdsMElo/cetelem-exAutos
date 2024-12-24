#!/bin/bash

# Criar um ambiente virtual
python3 -m venv .venv-exAutos

# Ativar o ambiente virtual
source .venv-exAutos/bin/activate

# Instalar as dependências
pip install -r requirements.txt
