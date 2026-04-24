@echo off
setlocal
title Headout Auto-Restart System

:: Change directory to the script's location to ensure paths work
cd /d "%~dp0"

:loop
cls
echo ==========================================
echo Starting Headout System Continuous Runner
echo Time: %TIME%
echo ==========================================

:: Check if virtual environment exists
if not exist venv (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv venv
    call venv\Scripts\activate
    echo [INFO] Installing requirements...
    pip install -r requirements.txt
    echo [INFO] Installing Playwright browsers...
    playwright install chromium
) else (
    :: Activate existing environment
    call venv\Scripts\activate
)

echo [INFO] Launching Python script (Headless Mode)...
:: Run the continuous runner in headless mode.
python headout_continuous_run.py --headless

echo.
echo [WARNING] Application stopped or crashed!
echo [INFO] Restarting in 5 seconds... Press Ctrl+C to abort.
timeout /t 5 >nul
goto loop
