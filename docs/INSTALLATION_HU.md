# Telepítés és terjesztés

## Windows – ajánlott telepítés

### Egyfájlos telepítő

A kiadási csomagban található `Offline-Audiobook-Creator-Setup-1.0.1.exe` a
klasszikus Windows-telepítő. A telepítő:

1. telepíti a programfájlokat, a Start menü-parancsikont és az opcionális
   asztali parancsikont;
2. ellenőrzi a Docker Desktopot és a WSL2-t;
3. hiányzó Docker Desktop esetén a `winget` segítségével meghívja a hivatalos
   Docker Desktop telepítőt, vagy tartalékként letölti a hivatalos telepítőt;
4. a Piper magyar és angol hangmodelleket is telepíti;
5. első indításkor a felhasználó írható `%LOCALAPPDATA%\Offline Audiobook
   Creator\data` könyvtárat használja az input, output és cache adatokhoz.

A Docker Desktop és a WSL2 telepítése rendszergazdai jóváhagyást, a WSL első
bekapcsolása pedig újraindítást kérhet. A Docker-képfelépítés első alkalommal
internetkapcsolatot igényel; az alkalmazás a kép elkészülte után helyben fut.

### Fejlesztői / Pythonos telepítés

1. Telepíts Python 3.10, 3.11, 3.12 vagy 3.13 verziót.
2. Telepítsd az FFmpeg-et, vagy hagyd, hogy a telepítő a `winget` segítségével
   megpróbálja feltenni.
3. Csomagold ki a projektet egy mappába.
4. Dupla kattintással futtasd a `setup-and-start.cmd` fájlt.

A telepítő létrehozza a `.venv` virtuális környezetet, telepíti a Python-
függőségeket, létrehozza az adatkönyvtárakat és letölti a magyar és angol Piper
hangmodelleket. A telepítés után a böngészőben megnyílik a helyi UI.

## EXE indító Dockerhez

Ha a csomag tartalmazza az `Offline-Audiobook-Creator-Launcher.exe` fájlt,
dupla kattintással indítható. Az indító:

1. ellenőrzi vagy elindítja a Docker Desktopot;
2. elindítja a `docker-compose.yml` alapján a konténert;
3. megvárja, amíg a webes API elérhető lesz;
4. megnyitja az alapértelmezett böngészőt a `http://127.0.0.1:8766` címen.

Hiba esetén a `%LOCALAPPDATA%\Offline Audiobook Creator\data` mappában
létrejön a `launcher.log` naplófájl.

Az EXE elkészítéséhez .NET 9 SDK szükséges:

```powershell
.\build-launcher.ps1 -SelfContained
```

A `-SelfContained` változat futtatásához a felhasználónak nem kell külön .NET
runtime-ot telepítenie.

Az Inno Setup telepítő buildeléséhez telepítsd az Inno Setupot, majd futtasd:

```powershell
winget install --exact --id JRSoftware.InnoSetup
.\build-installer.ps1 -Version 1.0.1
```

Ha a hangmodellek hiányoznak, a build script automatikusan letölti őket. A
letöltés kihagyásával végzett ellenőrzéshez használd a `-SkipModelDownload`
kapcsolót.

PowerShellből ugyanez:

```powershell
.\install-windows.ps1 -InstallFfmpeg
.\start-windows.ps1
```

Ha a hangmodelleket külön szeretnéd beszerezni:

```powershell
.\install-windows.ps1 -SkipModels
```

## Docker – NeMo-val

Docker Desktop futása után:

```powershell
docker compose build
$env:AUDIOBOOK_PORT=8766
docker compose up -d
```

Ezután nyisd meg: `http://127.0.0.1:8766`.

A Docker-konténer Linuxos Python-környezetben futtatja a NeMo Text Processinget.
A `models`, `inputs`, `outputs`, `work` és `work-ui` mappák a Windows géppel
közösek.

## Könyvtárak

| Mappa | Tartalom |
| --- | --- |
| `models` | Piper `.onnx` és `.onnx.json` hangmodellek |
| `inputs` | feldolgozandó dokumentumok |
| `outputs` | elkészült MP3-fájlok |
| `work` | CLI gyorsítótár és részeredmények |
| `work-ui` | webes munkamenetek és részeredmények |

## Natív Windows és NeMo

A natív Windowsos telepítő a Piper TTS-t és a beépített helyi normalizálót
telepíti. A NeMo/Pynini réteghez a Dockeres indítás javasolt, mert a Pynini
Windowsos pip-telepítése korlátozott.

