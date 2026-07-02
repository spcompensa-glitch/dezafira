@echo off
title INSTALADOR E INICIALIZADOR DEZAFIRA LOCAL STUDIO
color 0b

echo =====================================================================
echo           INICIALIZANDO PLATAFORMA DEZAFIRA LOCAL STUDIO
echo                Automacao Global e Foco em Monetizacao
echo =====================================================================
echo.

:: 1. Verificar dependencias do Node.js e instalar no frontend se necessario
echo [*] Configurando ambiente Frontend (Next.js)...
cd open-generative-ai
if not exist node_modules (
    echo [!] node_modules nao encontrado no Frontend. Executando npm install...
    call npm install
) else (
    echo [OK] Dependencias do Frontend ja instaladas.
)

:: Iniciar o Frontend em segundo plano em uma nova janela de terminal
echo [*] Iniciando servidor do Frontend na porta 3000...
start "Dezafira Frontend (Next.js)" cmd /c "npm run dev"
cd ..

:: 2. Verificar dependencias do Python e instalar no Backend se necessario
echo [*] Configurando ambiente Backend (FastAPI)...
cd SniperVideoEngine
if not exist venv (
    echo [!] Criando ambiente virtual Python venv...
    python -m venv venv
)
call venv\Scripts\activate
echo [*] Instalando dependencias do requirements.txt...
pip install -r requirements.txt

:: Iniciar o Backend
echo [*] Iniciando servidor do Backend na porta 8000...
echo.
echo =====================================================================
echo     [SUCESSO] A DEZAFIRA ESTA SUBINDO LOCALMENTE!
echo     - Front-end: http://localhost:3000
echo     - Back-end API: http://localhost:8000
echo =====================================================================
echo.
echo Pressione CTRL+C nesta janela para encerrar o backend.
echo.
uvicorn server:app --reload --port 8000
