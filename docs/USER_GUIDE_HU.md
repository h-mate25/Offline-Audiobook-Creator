# Offline Audiobook Creator 1.0 – felhasználói kézikönyv

Az Offline Audiobook Creator PDF, DOCX, TXT és Markdown dokumentumokból készít
magyar vagy angol nyelvű MP3-hangoskönyvet. A feldolgozás helyben történik:
feltöltött dokumentum, szöveg és hangfájl nem kerül külső szolgáltatásba.

## Gyors munkafolyamat

1. Töltsd be a dokumentumot a **Forrás** lépésben.
2. A **Hang** lépésben válaszd ki a nyelvet, a hangot és a természetességi beállítást.
3. A próbamondattal ellenőrizd a hangot.
4. A **Generálási szöveg** lépésben szerkeszd a felolvasandó szöveget.
5. Készíts rövid dokumentum-hangmintát.
6. A **Generálás** lépésben indítsd a teljes MP3 elkészítését.

## 1. Forrás

### Feltöltés

A **Feltöltés** mód a számítógépről kiválasztott PDF, DOCX, TXT vagy MD fájlt
használja. A fájlt a kijelölt területre húzva is megadhatod.

### Helyi útvonal

A **Helyi útvonal** mód akkor hasznos, ha a dokumentum már a gépen található.
Add meg a teljes Windows elérési utat, például:

```text
C:\Konyvek\sajat-konyv.pdf
```

### Kimeneti fájlnév

Opcionálisan megadhatod a kész MP3 nevét. Üres mező esetén az alkalmazás a
forrásfájlból képez nevet.

### Fájl betöltése és tovább

Beolvassa a dokumentumot, eltávolítja a tipikus PDF-zajokat, majd megjeleníti a
szerkeszthető szövegelőnézetet.

## 2. Hang

### Nyelv és hangmodell

A **Magyar** és **English** választó határozza meg a hangkörnyezetet. A
**Hangmodell** mezőben a telepített Piper hangok közül választhatsz.

### Szöveg-normalizálás

- **Automatikus:** NeMo Text Processing, ha elérhető; egyébként helyi szabályok.
- **Helyi szabályok:** Windows alatt is használható, külső normalizáló nélkül.
- **NeMo Text Processing:** szigorúan a NeMo-t használja; Dockerben támogatott.

A normalizálás a számokat, mértékegységeket, rövidítéseket és egyes írásjeleket
beszédbarátabb formára alakítja.

### Hangpresetek

- **Természetes:** kiegyensúlyozott alapbeállítás.
- **Nyugodt:** lassabb, nagyobb mondatszünetű megszólalás.
- **Gyorsabb:** rövidebb, feszesebb előadás.

A preset kiválasztása után minden érték kézzel módosítható.

### Alap hangparaméterek

- **Mondatszünet:** mondatok közötti alapértelmezett csend.
- **Tempó:** a beszéd sebessége; nagyobb érték lassabb beszédet jelent.
- **Szövegdarab méret:** a feldolgozási egységek mérete.

Az 1.0 alapbeállítása: 0,18 mp mondatszünet, 1,07-es tempó, 1200 karakteres
darabméret, Noise scale 0,28 és Noise width 0,11.

### Haladó Piper hangolás

A **Haladó Piper hangolás** rész alapból zárva van. A Noise scale és Noise
width ritkábban szükséges finomhangolás; első használatkor érdemes az alapértéket
megtartani.

### Hang tesztelése

Írj be egy rövid próbamondatot, majd kattints a **Hang tesztelése** gombra. A
hangminta a felületen lejátszható. Ezzel a teljes dokumentum generálása előtt
ellenőrizhető a nyelv, a hang, a tempó és a természetesség.

## 3. Generálási szöveg

A nagy szövegdoboz tartalmazza a ténylegesen felolvasandó szöveget. A generálás
előtt szabadon átírható.

### Szünetgombok

A kurzor helyére az alábbi gombok szúrnak be valódi csendet:

- **Szünet 0,3 mp**
- **Szünet 0,5 mp**
- **Szünet 1 mp**
- **Szünet 3 mp**
- **Szünet 5 mp**

### Rövid dokumentum-hangminta

A **Hangminta darabjai** mezőben állítható, hány első szövegdarabból készüljön
próba. A **Rövid dokumentum-hangminta** gomb csak ezt a rövid részletet dolgozza
fel. Az eredmény a gomb alatt lejátszható és letölthető.

## 4. Generálás

### Cache újragenerálása

Bekapcsolva figyelmen kívül hagyja a korábbi részeredményeket, és minden
szövegdarabot újra elkészít.

### Teljes MP3

A **Teljes MP3** gomb a teljes szerkesztett dokumentumból készít hangoskönyvet.
Nagy dokumentumoknál a feldolgozás hosszabb ideig tarthat; a részeredmények a
munka mappában megmaradnak.

### Futási napló és letöltés

A napló mutatja a feldolgozási darabokat, a gyorsítótár állapotát és az esetleges
hibákat. Sikeres elkészülés után az **MP3 letöltése** gombbal menthető a fájl.

## Hibaelhárítás

- **Nincs hangmodell:** futtasd újra a `install-windows.ps1` telepítőt, vagy
  ellenőrizd a `models` mappát.
- **FFmpeg nem található:** telepítsd az FFmpeg-et, majd indítsd újra az appot.
- **A NeMo nem elérhető Windows alatt:** használd az Automatikus vagy a Helyi
  szabályok módot, illetve indítsd Dockerben a NeMo-s környezetet.
- **Beolvasási gond PDF-nél:** a szkennelt, képként tárolt PDF-hez előbb OCR
  szükséges; az alkalmazás a kijelölhető szöveget olvassa.

