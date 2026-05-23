@echo off
title ASA Email Marketing - Setup
echo.
echo ============================================
echo  ASA Email Marketing - Instalacao
echo ============================================
echo.

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale em https://python.org
    pause
    exit /b 1
)

echo [1/3] Criando ambiente virtual...
if not exist "venv" (
    python -m venv venv
)

echo [2/3] Instalando dependencias...
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo [3/3] Iniciando o servidor...
echo.
echo ============================================
echo  Acesse: http://127.0.0.1:5000
echo  Para parar: pressione CTRL+C
echo ============================================
echo.
python app.py
pause
