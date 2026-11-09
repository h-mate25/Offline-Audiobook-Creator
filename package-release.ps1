[CmdletBinding()]
param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$releaseRoot = Join-Path $Root "release"
$packageName = "Offline-Audiobook-Creator-$Version-Windows"
$staging = Join-Path $releaseRoot $packageName
$archive = Join-Path $releaseRoot "$packageName.zip"

New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
if (Test-Path $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
if (Test-Path $archive) { Remove-Item -LiteralPath $archive -Force }
New-Item -ItemType Directory -Path $staging -Force | Out-Null

$items = @(
    ".dockerignore",
    ".gitignore",
    "Dockerfile",
    "CHANGELOG.md",
    "README.md",
    "docker-compose.yml",
    "build-launcher.ps1",
    "install-windows.ps1",
    "launcher",
    "package-release.ps1",
    "pyproject.toml",
    "setup-and-start.cmd",
    "start-windows.ps1",
    "docs",
    "src"
)

foreach ($relativePath in $items) {
    $source = Join-Path $Root $relativePath
    $destination = Join-Path $staging $relativePath
    if (Test-Path $source -PathType Container) {
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        Copy-Item -Path (Join-Path $source "*") -Destination $destination -Recurse -Force
    } else {
        $destinationDirectory = Split-Path -Parent $destination
        New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

Get-ChildItem -Path $staging -Directory -Filter "__pycache__" -Recurse -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $staging -Directory -Filter "*.egg-info" -Recurse -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $staging -Directory -Filter "bin" -Recurse -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $staging -Directory -Filter "obj" -Recurse -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $staging -Directory -Filter "publish" -Recurse -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force

$launcherExe = Join-Path $releaseRoot "Offline-Audiobook-Creator-Launcher.exe"
if (Test-Path $launcherExe) {
    Copy-Item -LiteralPath $launcherExe -Destination (Join-Path $staging "Offline-Audiobook-Creator-Launcher.exe") -Force
}

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $archive -CompressionLevel Optimal
Write-Host "Release csomag elkészült: $archive" -ForegroundColor Green

