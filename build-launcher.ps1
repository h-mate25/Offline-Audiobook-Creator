[CmdletBinding()]
param(
    [switch]$SelfContained
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Project = Join-Path $Root "launcher\OfflineAudiobookCreatorLauncher.csproj"
$Output = Join-Path $Root "release\launcher-publish"
$FinalExe = Join-Path $Root "release\Offline-Audiobook-Creator-Launcher.exe"

if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw "A .NET SDK nem található. Telepítsd a .NET 9 SDK-t, majd futtasd újra."
}

if (Test-Path $Output) { Remove-Item -LiteralPath $Output -Recurse -Force }
if (Test-Path $FinalExe) { Remove-Item -LiteralPath $FinalExe -Force }
New-Item -ItemType Directory -Path $Output -Force | Out-Null

$publishArgs = @(
    "publish", $Project,
    "--configuration", "Release",
    "--runtime", "win-x64",
    "--output", $Output,
    "/p:PublishSingleFile=true",
    "/p:IncludeNativeLibrariesForSelfExtract=true",
    "/p:EnableCompressionInSingleFile=true"
)
if ($SelfContained) { $publishArgs += "--self-contained" }
else { $publishArgs += "--no-self-contained" }

& dotnet @publishArgs
if ($LASTEXITCODE -ne 0) { throw "A launcher build sikertelen volt." }

Copy-Item -LiteralPath (Join-Path $Output "Offline-Audiobook-Creator-Launcher.exe") -Destination $FinalExe -Force
Write-Host "Launcher elkészült: $FinalExe" -ForegroundColor Green

