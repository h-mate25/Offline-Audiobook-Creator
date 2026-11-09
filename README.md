# Offline Audiobook Creator

Offline PDF-, DOCX-, TXT- és Markdown-dokumentumokból MP3-hangoskönyvet készítő
Windows-alkalmazás. A hanggenerálást a Piper TTS, az opcionális szövegnormalizálást
pedig a Dockerben futó NVIDIA NeMo Text Processing végzi.

## Funkciók

- PDF, DOCX, TXT és Markdown fájlok feldolgozása.
- Magyar és angol offline Piper hangok.
- Több száz oldalas dokumentumok darabolása és folytatható feldolgozása.
- Szerkeszthető szövegelőnézet a generálás előtt.
- Külön hangteszt rövid próbamondattal.
- Rövid dokumentum-hangminta lejátszása és letöltése.
- Kézzel beszúrható, 0,3 / 0,5 / 1 / 3 / 5 másodperces szünetek.
- Természetes, nyugodt és tömörebb beszédpresetek.
- Automatikus mondat-, tagmondat- és bekezdésszünetek.
- Webcímek és e-mail-címek beszédbarát előkészítése.
- Beépített és egyéni kiejtési szabályok rövidítésekhez és nevekhez.
- Dockeres, offline használatra alkalmas feldolgozás NeMo-támogatással.

## Követelmények

### Ajánlott Windows-felhasználóknak

- Windows 10 vagy Windows 11.
- Python 3.10–3.13 a natív telepítéshez.
- FFmpeg az MP3-fájlok összefűzéséhez.
- Docker Desktop és WSL2 a NeMo-normalizáláshoz vagy a Dockeres indításhoz.

A telepítő és a telepítőszkriptek ellenőrzik a szükséges összetevőket. Az első
telepítéskor internetkapcsolat kell a Python-függőségek, a Piper hangmodellek és
szükség esetén a Docker-kép letöltéséhez. A feldolgozás ezután helyben történik.

## Gyors kezdés Windows alatt

### Natív Pythonos indítás

1. Klónozd vagy töltsd le a repositoryt.
2. Dupla kattintással futtasd a `setup-and-start.cmd` fájlt.
3. A böngészőben nyisd meg a megjelenő helyi címet, alapértelmezés szerint:
   `http://127.0.0.1:8765`.

A szkript létrehozza a `.venv` virtuális környezetet, telepíti a függőségeket,
létrehozza az adatkönyvtárakat és letölti a magyar, illetve angol Piper
hangmodelleket.

PowerShellből ugyanez:

```powershell
.\\install-windows.ps1 -InstallFfmpeg
.\\start-windows.ps1
```

Ha a hangmodelleket külön szeretnéd beszerezni:

```powershell
.\\install-windows.ps1 -SkipModels
```

### Kiadási telepítő és indító

A kiadási csomag tartalmazhatja az `Offline-Audiobook-Creator-Setup-*.exe`
telepítőt és az `Offline-Audiobook-Creator-Launcher.exe` indítót. Ezek a Docker
Desktopot, a konténert és a böngészőben megnyíló helyi felületet kezelik.

A kész kiadások a [GitHub Releases](https://github.com/h-mate25/Offline-Audiobook-Creator/releases)
oldalon találhatók. A bináris kiadási fájlokat nem tároljuk a forráskód
repositoryjában.

## Dockeres indítás

Docker Desktop futása után:

```powershell
docker compose build
$env:AUDIOBOOK_PORT = "8766"
docker compose up -d
```

Ezután nyisd meg: `http://127.0.0.1:8766`.

Leállítás:

```powershell
docker compose down
```

A Docker-konténer Linuxos Python-környezetben futtatja a NeMo Text Processinget.
Az `AUDIOBOOK_DATA_DIR` környezeti változóval külön, felhasználói írható
adatmappa adható meg:

```powershell
$env:AUDIOBOOK_DATA_DIR = "C:/Users/<felhasználó>/Offline Audiobook Creator/data"
$env:AUDIOBOOK_PORT = "8766"
docker compose up -d
```

## Használat

A webes felület négy lépésből áll:

1. **Forrás** – PDF, DOCX, TXT vagy Markdown dokumentum feltöltése.
2. **Hangteszt** – nyelv, hang és Piper-paraméterek kipróbálása egy rövid mondattal.
3. **Szöveg** – a tisztított, felolvasásra előkészített szöveg ellenőrzése és szerkesztése.
4. **Generálás** – a teljes MP3 elkészítése és letöltése.

A részletes gomb- és beállításleírást a webapp **Felhasználói útmutató** gombja
és a [magyar felhasználói kézikönyv](docs/USER_GUIDE_HU.md) tartalmazza.

## Természetesebb beszéd beállításai

A **Webcímek kezelése** beállítás három módot támogat:

- `domain` – csak a domain marad meg, például `example.com`;
- `skip` – a webcím kimarad a felolvasásból;
- `full` – a teljes cím megmarad, de beszédbarát alakban készül elő.

A **Természetes tagolási szünetek** bekezdéseknél és tagmondatoknál illesztenek
be óvatos extra csendet. Az alap mondatszünetet továbbra is a Piper
**Mondatszünet** beállítása adja.

Az **Egyéni kiejtési javítások** mezőben soronként adható meg szabály:

```text
Kft. = káefté
AI = ááj
```

Parancssorból ugyanez:

```powershell
.\\.venv\\Scripts\\audiobook-maker.exe make .\\book.pdf --language hu `
  --preset natural --link-mode domain `
  --pronunciation-file .\\pronunciations.txt
```

Az aktuális változat CPU-alapú. CUDA- és NVIDIA-GPU-gyorsítás nincs bekapcsolva;
a Piper hanggenerálás és a NeMo szövegnormalizálás helyben fut.

## Parancssoros használat

```powershell
.\\.venv\\Scripts\\audiobook-maker.exe make .\\book.pdf --language hu
.\\.venv\\Scripts\\audiobook-maker.exe make .\\book.docx `
  --language en --output .\\outputs\\book-en.mp3
```

Hasznos természetességi kapcsolók:

```text
--preset {natural,calm,compact}
--link-mode {domain,skip,full}
--no-dynamic-pauses
--pronunciation-file <UTF-8 fájl>
```

## Adatkönyvtárak

| Mappa | Tartalom |
| --- | --- |
| `models` | Piper `.onnx` és `.onnx.json` hangmodellek |
| `inputs` | feldolgozandó dokumentumok |
| `outputs` | elkészült MP3-fájlok |
| `work` | CLI-gyorsítótár és részeredmények |
| `work-ui` | webes munkamenetek és részeredmények |

Ezek a mappák felhasználói adatokat tartalmazhatnak, ezért nem kerülnek a
Git repositoryba.

## Fejlesztés

```powershell
py -3.13 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -e .
python -m compileall -q src
node --check src\\audiobook_maker\\static\\app.js
```

A szövegfeldolgozási tesztek futtatása (a tesztfájlok pytest-kompatibilisek):

```powershell
$env:PYTHONPATH = "src"
python -m pip install pytest
python -m pytest
```

Windows-telepítő buildelése:

```powershell
winget install --exact --id JRSoftware.InnoSetup
.\\build-installer.ps1 -Version 1.0.1
```

Docker-indító buildelése:

```powershell
.\\build-launcher.ps1 -SelfContained
```

## Projektstruktúra

```text
src/audiobook_maker/   alkalmazáskód és webes felület
docs/                  telepítési és felhasználói dokumentáció
installer/             Inno Setup konfiguráció
launcher/              Docker-indító Windows alkalmazás
tests/                 tesztek
Dockerfile             NeMo-kompatibilis Docker-környezet
docker-compose.yml     helyi konténerindítás
```

## Korlátok

- A csak képet tartalmazó, szkennelt PDF-ekhez külön OCR-lépés szükséges.
- A program a kijelölhető szöveget tudja közvetlenül feldolgozni.
- A NeMo Text Processing a Dockeres módban érhető el teljes körűen; natív
  Windows alatt az automatikus mód a helyi szabályokra válthat.
- A feldolgozás sebessége a dokumentum hosszától, a Piper hangmodelltől és a
  számítógép teljesítményétől függ.

## Dokumentáció

- [Telepítés és terjesztés](docs/INSTALLATION_HU.md)
- [Magyar felhasználói kézikönyv](docs/USER_GUIDE_HU.md)
- [Változásnapló](CHANGELOG.md)

## Licenc

A repository jelenleg nem tartalmaz `LICENSE` fájlt. A projekt licencelését a
szerzőnek kell megadnia, mielőtt a kódot mások újra felhasználnák vagy
terjesztenék.

