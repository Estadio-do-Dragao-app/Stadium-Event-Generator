@echo off
echo.
echo ESTADIO DO DRAGAO - Simulacao de Evacuacao
echo.

REM Cria venv se não existir
if not exist "venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    python -m venv venv
    echo.
)

REM Ativa venv
call venv\Scripts\activate.bat

REM Força instalação das dependências essenciais (mesmo que requirements.txt falhe)
echo Instalando/atualizando dependencias...
python -m pip install --upgrade pip -q
pip install tqdm opencv-python numpy matplotlib pysocialforce numba==0.58.1 paho-mqtt pandas

REM Se houver requirements.txt, usa-o também
if exist requirements.txt (
    python -m pip install -r requirements.txt -q
)

echo.
echo A iniciar simulacao...
cd simulator
python -m dragao_simulator

echo.
echo Simulacao terminada. Resultados em ../outputs/
pause