[CmdletBinding()]
param(
    [switch]$SkipModels,
    [switch]$InstallFfmpeg
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Program,
        [Parameter(ValueFromRemainingArguments = $true)][object[]]$Arguments
    )

    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "A parancs sikertelenül fejeződött be: $Program $($Arguments -join ' ')"
    }
}

Write-Host "Offline Audiobook Creator 1.0 - Windows telepítő" -ForegroundColor Cyan
Write-Host "Telepítési mappa: $Root"

$pythonCommand = $null
$pythonArguments = @()
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue

if ($pyLauncher) {
    foreach ($minor in 13, 12, 11, 10) {
        $candidateArguments = @("-3.$minor")
        $candidateVersion = & py @candidateArguments -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidateVersion) {
            $pythonCommand = "py"
            $pythonArguments = $candidateArguments
            break
        }
    }
}

if (-not $pythonCommand) {
    $pythonExecutable = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonExecutable) {
        $pythonCommand = $pythonExecutable.Source
    }
}

if (-not $pythonCommand) {
    throw "Python 3.10-3.13 nem található. Telepítsd a python.org-ról, majd futtasd újra ezt a telepítőt."
}

$pythonVersionText = (& $pythonCommand @pythonArguments -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))").Trim()
$pythonVersion = [version]$pythonVersionText
if ($pythonVersion -lt [version]"3.10" -or $pythonVersion -ge [version]"3.14") {
    throw "Nem támogatott Python-verzió: $pythonVersionText. A támogatott tartomány: 3.10-3.13."
}
Write-Host "Python: $pythonVersionText" -ForegroundColor Green

$venvPath = Join-Path $Root ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Virtuális környezet létrehozása..." -ForegroundColor Yellow
    Invoke-Checked $pythonCommand ($pythonArguments + @("-m", "venv", $venvPath))
}

Write-Host "Python-függőségek telepítése..." -ForegroundColor Yellow
Invoke-Checked $venvPython @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked $venvPython @("-m", "pip", "install", "-e", ".")

foreach ($directory in @("models", "inputs", "outputs", "work", "work-ui")) {
    New-Item -ItemType Directory -Path (Join-Path $Root $directory) -Force | Out-Null
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    if ($InstallFfmpeg -and (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "FFmpeg telepítése a winget segítségével..." -ForegroundColor Yellow
        Invoke-Checked winget @(
            "install", "--id", "Gyan.FFmpeg.Shared", "--exact",
            "--accept-source-agreements", "--accept-package-agreements"
        )
    } else {
        Write-Warning "Az FFmpeg nem található a PATH-ban. Telepítsd a https://ffmpeg.org/ oldalról, vagy futtasd: .\install-windows.ps1 -InstallFfmpeg"
    }
}

if (-not $SkipModels) {
    $modelsPath = Join-Path $Root "models"
    $models = @(
        @{ Name = "hu_HU-anna-medium.onnx"; Url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/hu/hu_HU/anna/medium/hu_HU-anna-medium.onnx" },
        @{ Name = "hu_HU-anna-medium.onnx.json"; Url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/hu/hu_HU/anna/medium/hu_HU-anna-medium.onnx.json" },
        @{ Name = "en_US-lessac-medium.onnx"; Url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" },
        @{ Name = "en_US-lessac-medium.onnx.json"; Url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" }
    )

    foreach ($model in $models) {
        $destination = Join-Path $modelsPath $model.Name
        if (Test-Path $destination) {
            Write-Host "Már megvan: $($model.Name)" -ForegroundColor DarkGreen
            continue
        }
        Write-Host "Hangmodell letöltése: $($model.Name)" -ForegroundColor Yellow
        Invoke-WebRequest -Uri $model.Url -OutFile $destination -UseBasicParsing
    }
} else {
    Write-Host "Hangmodellek letöltése kihagyva (-SkipModels)." -ForegroundColor DarkYellow
}

Write-Host "" 
Write-Host "Telepítés kész." -ForegroundColor Green
Write-Host "Indítás: .\start-windows.ps1"
Write-Host "Vagy dupla kattintás: .\setup-and-start.cmd"

