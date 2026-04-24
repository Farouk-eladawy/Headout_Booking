# Headout System - Auto Setup Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Headout Scraper - Automated Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "✓ $pythonVersion found" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found! Please install Python 3.8+" -ForegroundColor Red
    exit
}

# Create virtual environment
Write-Host "[2/5] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
} else {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate and install dependencies
Write-Host "[3/5] Installing dependencies..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt --quiet
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Install Playwright browsers
Write-Host "[4/5] Installing Playwright browser..." -ForegroundColor Yellow
playwright install chromium
Write-Host "✓ Chromium installed" -ForegroundColor Green

# Create directories
Write-Host "[5/5] Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "data" -Force | Out-Null
New-Item -ItemType Directory -Path "logs" -Force | Out-Null
Write-Host "✓ Directories created" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit 'headout_config.env' with your credentials"
Write-Host "2. Run: python headout_scraper.py --server"
Write-Host ""
Write-Host "Or use: .\start_headout.bat" -ForegroundColor Cyan
