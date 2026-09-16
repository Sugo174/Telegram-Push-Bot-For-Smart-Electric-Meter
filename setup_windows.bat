@echo off
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"

if errorlevel 1 (
    echo.
    echo Could not create the shortcut.
    pause
    exit /b 1
)

echo.
echo Shortcut created on the desktop.
pause