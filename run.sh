#!/bin/bash

echo
echo "ESTÁDIO DO DRAGÃO – Simulação de Evacuação"
echo

# Cria venv se não existir
[ ! -d "venv" ] && echo "Criando ambiente virtual..." && python3 -m venv venv

# Ativa venv
source venv/bin/activate

# Força instalação das dependências essenciais
echo "Instalando/atualizando dependências..."
pip install --upgrade pip -q
pip install tqdm opencv-python numpy matplotlib pysocialforce numba==0.58.1 paho-mqtt pandas

# Se houver requirements.txt, usa-o também
[ -f requirements.txt ] && pip install -r requirements.txt -q

echo
echo "A iniciar simulação..."
cd simulator
python -m dragao_simulator

echo
echo "Simulação concluída. Resultados em ../outputs/"
read -p "Pressione Enter para fechar..."