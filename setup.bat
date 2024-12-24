@echo off

:: Criar o ambiente virtual
python -m venv .venv-exAutos

:: Ativar o ambiente virtual
call .venv-exAutos\Scripts\activate

:: Instalar as dependências
pip install -r requirements.txt
