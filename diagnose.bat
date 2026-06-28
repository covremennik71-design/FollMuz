@echo off
title FollMuz - Diagnostics
cd /d "%~dp0"

echo ================================================
echo         FollMuz - Diagnostics
echo ================================================
echo.

echo [1/6] Python version:
python --version
if errorlevel 1 (
    echo [ERROR] Python not found!
    goto :end
)
echo.

echo [2/6] Python path:
where python
echo.

echo [3/6] Testing imports:
echo - Testing flask...
python -c "import flask; print('  [OK] flask', flask.__version__)" 2>&1
if errorlevel 1 echo [FAIL] flask not installed

echo - Testing mutagen...
python -c "import mutagen; print('  [OK] mutagen', mutagen.version)" 2>&1
if errorlevel 1 echo [FAIL] mutagen not installed

echo - Testing yt_dlp...
python -c "import yt_dlp; print('  [OK] yt_dlp', yt_dlp.version.__version__)" 2>&1
if errorlevel 1 echo [FAIL] yt_dlp not installed
echo.

echo [4/6] FFmpeg:
where ffmpeg 2>&1
if errorlevel 1 echo [WARNING] FFmpeg not found in PATH
echo.

echo [5/6] Testing app.py import:
python -c "import sys; sys.path.insert(0, '.'); import app; print('[OK] app.py imported successfully')" 2>&1
if errorlevel 1 (
    echo [FAIL] app.py import failed
    echo.
    echo Full error:
    python -c "import sys; sys.path.insert(0, '.'); import app" 2>&1
)
echo.

echo [6/6] Testing server startup (will exit after 2 seconds):
start /b python -c "import sys; sys.path.insert(0, '.'); import app; print('Server starting...'); import threading; threading.Timer(2, lambda: sys.exit(0)).start(); app.app.run(port=5001, debug=False, use_reloader=False)" 2>&1
timeout /t 3 /nobreak >nul
echo.

:end
echo ================================================
echo Diagnostics complete.
echo ================================================
pause
