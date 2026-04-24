@echo off
echo ========================================
echo Headout Scraper - Quick Start
echo ========================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
    playwright install chromium
) else (
    call venv\Scripts\activate.bat
)

echo.
echo Starting Headout Scraper in Server Mode...
echo Press Ctrl+C to stop
echo.

python headout_scraper.py --server

pause
