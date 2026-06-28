@echo off
cd /d "%~dp0"
start /min "" "%SystemRoot%\system32\WindowsPowerShell\v1.0\powershell.exe" -WindowStyle Hidden -NoProfile -Command "python tg_bot.py"
