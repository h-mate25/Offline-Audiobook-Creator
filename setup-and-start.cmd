@echo off
setlocal
cd /d "%~dp0"

echo Offline Audiobook Creator 1.0 telepitese es inditasa...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows.ps1" -InstallFfmpeg
if errorlevel 1 (
    echo A telepites sikertelen volt.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-windows.ps1"
if errorlevel 1 pause

