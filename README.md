# Offline Audiobook Creator 1.0

Offline PDF/DOCX/TXT/Markdown → MP3 hangoskönyv-készítő Piper TTS-sel.

## 1.0 funkciók

- PDF, DOCX, TXT és MD dokumentumok beolvasása.
- Magyar és angol offline Piper hangok.
- Több száz oldalas dokumentumok biztonságos darabolása.
- PDF-zajok és linkfeliratok tisztítása.
- Szerkeszthető felolvasási előnézet generálás előtt.
- Hangteszt egy rövid próbamondattal.
- Rövid dokumentum-hangminta lejátszással és letöltéssel.
- 0,3 / 0,5 / 1 / 3 / 5 másodperces beszúrható szünetek.
- Természetes, nyugodt és gyorsabb hangpresetek.
- Automatikus NeMo → helyi normalizálás.
- Folytatható feldolgozás cache-sel.
- Dockeres Linux-környezet NeMo-támogatással.

## Rendes Windows-telepítő

A `Offline-Audiobook-Creator-Setup-1.0.1.exe` telepítő létrehozza a program
mappáját, a Start menü- és opcionális asztali parancsikont, valamint az első
telepítéskor ellenőrzi a Docker Desktopot és a WSL2-t. Ha a Docker Desktop
hiányzik és a `winget` elérhető, a telepítő meghívja a hivatalos Docker Desktop
csomag telepítőjét. A Piper magyar és angol hangmodellek az installer részei.

A telepítő a felhasználó írható AppData-mappáját használja az input, output és
cache adatokhoz, ezért a programnak nem kell a Program Files mappájába írnia.
A Docker-képfelépítés első alkalommal internetkapcsolatot igényel; utána a
feldolgozás helyben, a Docker-konténerben történik.

Fejlesztői gépen a telepítő újraépítése:

```powershell
winget install --exact --id JRSoftware.InnoSetup
.\build-installer.ps1 -Version 1.0.1
```

Ha a `models` mappában hiányoznak a hangmodellek, a build script automatikusan
letölti a hivatalos magyar és angol Piper fájlokat.

## Gyors telepítés Windowsra

Töltsd le vagy klónozd a repositoryt, majd dupla kattintással futtasd:

```text
setup-and-start.cmd
```

Ez létrehozza a `.venv` környezetet, telepíti a Python-függőségeket, ellenőrzi
az FFmpeg-et, letölti a magyar és angol Piper hangmodelleket, majd elindítja a
helyi webappot.

PowerShellből:

```powershell
.\install-windows.ps1 -InstallFfmpeg
.\start-windows.ps1
```

Dockeres használatnál az `Offline-Audiobook-Creator-Launcher.exe` elindítja a
konténert, megvárja a webes felületet, majd megnyitja az alapértelmezett
böngészőt a `http://127.0.0.1:8766` címen. A telepítő ezt a launchert a Start
menübe és – ha kéred – az asztalra is kihelyezi.

A részletes telepítési leírás: [docs/INSTALLATION_HU.md](docs/INSTALLATION_HU.md).

## Használat

Indítás után nyisd meg: `http://127.0.0.1:8765`.

Az alkalmazás négy lépésben működik: **Forrás → Hangteszt → Szöveg →
Generálás**. A teljes felhasználói kézikönyv a webapp jobb felső sarkában lévő
**Felhasználói útmutató** gombból és a [docs/USER_GUIDE_HU.md](docs/USER_GUIDE_HU.md)
fájlból érhető el.

## CLI példa

```powershell
.\.venv\Scripts\audiobook-maker.exe make .\book.pdf --language hu
.\.venv\Scripts\audiobook-maker.exe make .\book.docx --language en --output .\outputs\book-en.mp3
```

## Docker és NeMo

Docker Desktop futása után:

```powershell
docker compose build
$env:AUDIOBOOK_PORT=8766
docker compose up -d
```

Ezután: `http://127.0.0.1:8766`.

A Dockeres változat Linuxos Python-környezetben futtatja a NeMo Text Processinget.
Natív Windows alatt az Automatikus mód szükség esetén a helyi szabályokra vált.

## Mappák

| Mappa | Tartalom |
| --- | --- |
| `models` | Piper hangmodellek |
| `inputs` | bemeneti dokumentumok |
| `outputs` | elkészült MP3-fájlok |
| `work` / `work-ui` | cache és munkameneti részeredmények |

## Fejlesztői telepítés

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
node --check src\audiobook_maker\static\app.js
python -m compileall -q src
```

## Megjegyzések

Szkennelt, csak képet tartalmazó PDF-hez OCR szükséges. A program a kijelölhető
szöveget tudja közvetlenül feldolgozni.

