@echo off
chcp 65001 >nul
title FollMuz - Building EXE

echo ================================================
echo         Building FollMuz EXE
echo ================================================
echo.

:: Check requirements
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not found. Run install.bat first.
    pause
    exit /b 1
)

if not exist "FollMuz.spec" (
    echo [ERROR] FollMuz.spec not found
    pause
    exit /b 1
)

echo Running PyInstaller...
echo.

pyinstaller FollMuz.spec

if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo Build complete!
    echo EXE: dist\FollMuz\FollMuz.exe
    echo ================================================
) else (
    echo.
    echo ================================================
    echo Build failed. Check output above.
    echo ================================================
)

echo.
pause
