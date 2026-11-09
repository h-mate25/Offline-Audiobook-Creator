[CmdletBinding()]
param(
    [switch]$InstallDocker,
    [switch]$InstallWsl,
    [string]$DataRoot = ""
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[Offline Audiobook Creator] $Message" -ForegroundColor Cyan
}

function Invoke-Checked([string]$FilePath, [string[]]$ArgumentList) {
    Write-Step ("Indítás: {0} {1}" -f $FilePath, ($ArgumentList -join " "))
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -notin @(0, 3010)) {
        throw ("A(z) {0} sikertelenül futott (kód: {1})." -f $FilePath, $LASTEXITCODE)
    }
}

if ($DataRoot) {
    foreach ($folder in @("models", "inputs", "outputs", "work", "work-ui")) {
        New-Item -ItemType Directory -Path (Join-Path $DataRoot $folder) -Force | Out-Null
    }
}

if ($InstallWsl) {
    $wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
    if (-not $wsl) {
        $wingetForWsl = Get-Command winget.exe -ErrorAction SilentlyContinue
        if ($wingetForWsl) {
            Write-Step "A WSL2 nem található, a Microsoft WSL csomag telepítése indul."
            Invoke-Checked $wingetForWsl.Source @(
                "install", "--exact", "--id", "Microsoft.WSL", "--source", "winget",
                "--silent", "--accept-package-agreements", "--accept-source-agreements"
            )
            Write-Host "A WSL2 telepítése után lehet, hogy újra kell indítani a Windowst." -ForegroundColor Yellow
        } else {
            Write-Host "A wsl.exe és a winget sem található; a Docker Desktop telepítője még megpróbálhatja a szükséges WSL-komponensek telepítését." -ForegroundColor Yellow
        }
    } else {
        & wsl.exe --set-default-version 2 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Step "WSL2 alapértelmezett verzió beállítva."
        } else {
            Write-Host "A WSL2 alapértelmezett verzióját most nem sikerült beállítani; a Docker telepítője még megpróbálkozhat vele." -ForegroundColor Yellow
        }
    }
}

if ($InstallDocker) {
    $docker = Get-Command docker.exe -ErrorAction SilentlyContinue
    if ($docker) {
        Write-Step "A Docker CLI már telepítve van: $($docker.Source)"
    } else {
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if ($winget) {
            Write-Step "A Docker Desktop telepítése a Windows Package Managerrel indul."
            Invoke-Checked $winget.Source @(
                "install", "--exact", "--id", "Docker.DockerDesktop", "--source", "winget",
                "--silent", "--accept-package-agreements", "--accept-source-agreements"
            )
        } else {
            Write-Step "A winget nem található, a hivatalos Docker Desktop telepítő letöltése indul."
            $installer = Join-Path ([IO.Path]::GetTempPath()) "Docker Desktop Installer.exe"
            $downloadUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
            Invoke-WebRequest -Uri $downloadUrl -OutFile $installer -UseBasicParsing
            try {
                $process = Start-Process -FilePath $installer -ArgumentList @("install", "--quiet", "--accept-license") -Wait -PassThru
                if ($process.ExitCode -notin @(0, 3010)) {
                    throw "A Docker Desktop telepítője sikertelenül futott (kód: $($process.ExitCode))."
                }
            } finally {
                Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Write-Step "A függőség-ellenőrzés befejeződött."

