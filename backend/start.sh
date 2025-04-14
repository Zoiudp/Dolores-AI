#!/bin/bash

# Executa o init.py apenas uma vez na inicialização
echo "Executando init.py..."
python init.py

# Inicia o app principal
echo "Iniciando app.py..."
python -u app.py
