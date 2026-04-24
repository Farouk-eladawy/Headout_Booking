@echo off
setlocal
title Push to GitHub Repository

:: Check if git is installed
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH. Please install Git first.
    pause
    exit /b
)

:: Initialize git repository if not already initialized
if not exist .git (
    echo [INFO] Initializing new Git repository...
    git init
)

:: Add all files
echo [INFO] Adding files to Git...
git add .

:: Commit
set /p commit_msg="Enter commit message (or press enter for default 'Update Headout System'): "
if "%commit_msg%"=="" set commit_msg=Update Headout System
git commit -m "%commit_msg%"

:: Set main branch
git branch -M main

:: Check if remote 'origin' exists, if not add it. If it exists, update it.
git remote -v | findstr "origin" >nul
if %errorlevel% equ 0 (
    echo [INFO] Remote 'origin' exists. Updating URL...
    git remote set-url origin https://github.com/Farouk-eladawy/Headout_Booking.git
) else (
    echo [INFO] Adding remote 'origin'...
    git remote add origin https://github.com/Farouk-eladawy/Headout_Booking.git
)

:: Push code
echo [INFO] Pushing to GitHub...
:: If it's the first push, we need -u origin main
git push -u origin main

if %errorlevel% equ 0 (
    echo [SUCCESS] Code pushed to GitHub successfully!
) else (
    echo [ERROR] Failed to push code. Please check your GitHub credentials or repository permissions.
)

pause