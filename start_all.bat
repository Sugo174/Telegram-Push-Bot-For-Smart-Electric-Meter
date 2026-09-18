@echo off
cd /d "%~dp0"

start "Smart Meter PUSH Server" cmd /k python push_server.py
timeout /t 1 /nobreak > nul
start "Smart Meter Telegram Bot" cmd /k python app.py