[CmdletBinding()]
param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "A virtuális környezet még nincs telepítve; a telepítő elindul..." -ForegroundColor Yellow
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "install-windows.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning "FFmpeg nem található a PATH-ban. Az MP3-összefűzés hibázhat."
}

$url = "http://127.0.0.1:$Port"
Write-Host "Offline Audiobook Creator fut: $url" -ForegroundColor Cyan
Start-Process $url
& $venvPython -m audiobook_maker.cli ui --host 127.0.0.1 --port $Port
exit $LASTEXITCODE

