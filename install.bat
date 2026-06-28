@echo off
title FollMuz - Install Dependencies
cd /d "%~dp0"

echo ================================================
echo      FollMuz - Installing Dependencies
echo ================================================
echo.

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo.
    echo Download Python from: https://www.python.org/
    echo IMPORTANT: Check "Add Python to PATH" during installation
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] %PYVER%
echo.

echo Installing required packages...
echo.

echo [1/3] Installing Flask...
python -m pip install flask --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install Flask
    pause
    exit /b 1
)
echo [OK] Flask installed

echo.
echo [2/3] Installing Mutagen...
python -m pip install mutagen --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install Mutagen
    pause
    exit /b 1
)
echo [OK] Mutagen installed

echo.
echo [3/3] Installing yt-dlp...
python -m pip install yt-dlp --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install yt-dlp
    pause
    exit /b 1
)
echo [OK] yt-dlp installed

echo.
echo ================================================
echo [OK] All dependencies installed successfully!
echo ================================================
echo.
echo You can now run start.vbs or run.bat
echo.
pause
