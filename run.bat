@echo off
:: ─────────────────────────────────────────────────────────
::  ElderAssist — Windows Startup Script
::  Double-click to run, or execute from Command Prompt
:: ─────────────────────────────────────────────────────────

title ElderAssist AI Voice Assistant

echo.
echo   ╔═══════════════════════════════════════╗
echo   ║         🎙️  ElderAssist AI             ║
echo   ║   Multilingual Voice Assistant        ║
echo   ╚═══════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

:: Check ffmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] ffmpeg not found. Whisper needs ffmpeg.
    echo   Install: winget install ffmpeg
    echo   OR download from: https://ffmpeg.org/download.html
    echo.
)

:: Create virtual environment if missing
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate
call venv\Scripts\activate.bat

:: Install dependencies
echo Installing dependencies (first run may take a few minutes)...
pip install -q --upgrade pip
pip install -q -r requirements.txt

:: Create required directories
if not exist "static\audio" mkdir static\audio
if not exist "data" mkdir data

:: Set env vars
set FLASK_ENV=development
set WHISPER_MODEL=base
set PORT=5000
set HOST=0.0.0.0

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   Starting ElderAssist...
echo   URL: http://localhost:5000
echo   Whisper model: %WHISPER_MODEL%
echo   Press Ctrl+C to stop
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

:: Open browser after 5 seconds
start /min timeout /t 5 /nobreak >nul && start http://localhost:5000

:: Launch
python app.py

pause
