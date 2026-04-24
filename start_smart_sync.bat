@echo off
echo ========================================
echo Headout Scraper - Smart Sync Mode
echo ========================================
echo.
echo This mode preserves manual edits in Airtable unless Headout data actually changes.
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
echo Starting Headout Smart Sync...
echo Press Ctrl+C to stop
echo.

python headout_continuous_run_smart.py

pause
