@echo off
setlocal enabledelayedexpansion
title FollMuz - Startup
cd /d "%~dp0"

echo ================================================
echo         FollMuz - Starting Web Server
echo ================================================
echo.

:: Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo.
    echo Install Python from https://www.python.org/
    echo Make sure to check "Add Python to PATH"
    goto :error_exit
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] %PYVER%
echo.

:: Check all dependencies at once
echo [2/5] Checking dependencies...
python -c "import flask; import mutagen; import yt_dlp" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Missing dependencies!
    echo.
    echo Install with:
    echo pip install flask mutagen yt-dlp
    goto :error_exit
)
echo [OK] All dependencies installed
echo.

:: Check FFmpeg
echo [3/5] Checking FFmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARNING] FFmpeg not found in PATH
    echo Some features may not work.
    echo.
) else (
    echo [OK] FFmpeg found
)
echo.

:: Check port 5000
echo [4/5] Checking port 5000...
netstat -ano | findstr ":5000" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 5000 is busy, freeing...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000"') do (
        taskkill /PID %%a /F >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
    echo [OK] Port freed
) else (
    echo [OK] Port 5000 is free
)
echo.

:: Delete old error log
if exist error.log del error.log

:: Start server
echo [5/5] Starting server...
echo.
echo Server will run in background mode.
echo This window will close automatically.
echo.
echo Server URL: http://127.0.0.1:5000
echo.
echo To stop server:
echo   - Task Manager: kill pythonw.exe
echo   - Or run: taskkill /IM pythonw.exe /F
echo.
echo ================================================
echo.

:: Start pythonw.exe hidden with error logging
start "" /b pythonw.exe app.py 2> error.log

:: Wait for server to start
echo Waiting for server to start...
timeout /t 3 /nobreak >nul

:: Check if server is running
powershell -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:5000' -TimeoutSec 2 -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Server failed to start!
    echo.
    if exist error.log (
        echo Error log:
        echo ================================================
        type error.log
        echo ================================================
        echo.
    )
    goto :error_exit
)

echo [OK] Server started successfully!
echo.
echo Opening browser...
start http://127.0.0.1:5000
echo.
echo Done! Window will close in 3 seconds...
timeout /t 3 /nobreak >nul
exit /b 0

:error_exit
echo.
echo ================================================
echo Press any key to close this window...
pause >nul
exit /b 1
