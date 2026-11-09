[CmdletBinding()]
param(
    [string]$Version = "1.0.1",
    [switch]$SkipModelDownload
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LauncherBuild = Join-Path $Root "build-launcher.ps1"
$InstallerScript = Join-Path $Root "installer\OfflineAudiobookCreator.iss"
$Output = Join-Path $Root "release\Offline-Audiobook-Creator-Setup-$Version.exe"

if (-not (Test-Path $LauncherBuild)) { throw "A launcher build script nem található: $LauncherBuild" }
if (-not (Test-Path $InstallerScript)) { throw "Az Inno Setup script nem található: $InstallerScript" }

$modelManifest = @(
    @{ Name = "hu_HU-anna-medium.onnx"; Url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/hu/hu_HU/anna/medium/hu_HU-anna-medium.onnx" },
    @{ Name = "hu_HU-anna-medium.onnx.json"; Url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/hu/hu_HU/anna/medium/hu_HU-anna-medium.onnx.json" },
    @{ Name = "en_US-lessac-medium.onnx"; Url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" },
    @{ Name = "en_US-lessac-medium.onnx.json"; Url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" }
)

$modelsPath = Join-Path $Root "models"
New-Item -ItemType Directory -Path $modelsPath -Force | Out-Null
foreach ($model in $modelManifest) {
    $destination = Join-Path $modelsPath $model.Name
    if (Test-Path $destination) { continue }
    if ($SkipModelDownload) {
        throw "Hiányzó hangmodell: $($model.Name). Futtasd a buildet -SkipModelDownload nélkül, vagy helyezd a fájlt a models mappába."
    }
    Write-Host "Hiányzó hangmodell letöltése: $($model.Name)" -ForegroundColor Yellow
    Invoke-WebRequest -Uri $model.Url -OutFile $destination -UseBasicParsing
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $LauncherBuild -SelfContained
if ($LASTEXITCODE -ne 0) { throw "A self-contained launcher build sikertelen volt." }

$isccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)
$iscc = $isccCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) {
    $isccCommand = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($isccCommand) { $iscc = $isccCommand.Source }
}
if (-not $iscc) {
    throw "Az Inno Setup fordító (ISCC.exe) nem található. Telepítsd: winget install --exact --id JRSoftware.InnoSetup"
}

New-Item -ItemType Directory -Path (Split-Path -Parent $Output) -Force | Out-Null
& $iscc "/DMyAppVersion=$Version" $InstallerScript
if ($LASTEXITCODE -ne 0) { throw "Az Inno Setup telepítő build sikertelen volt." }

if (-not (Test-Path $Output)) { throw "A telepítő nem jött létre: $Output" }
Write-Host "Windows telepítő elkészült: $Output" -ForegroundColor Green

