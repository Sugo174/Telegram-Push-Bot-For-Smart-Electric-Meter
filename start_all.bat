@echo off
cd /d "%~dp0"

start "EMIS PUSH Server" cmd /k python push_server.py
timeout /t 1 /nobreak > nul
start "EMIS Telegram Bot" cmd /k python app.py