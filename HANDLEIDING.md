# BoekScanner — Handleiding

> **Tip:** ook als u dit niet leest, vindt u dezelfde uitleg
> rechtstreeks in de app onder de gele knop **❓ Hulp** rechtsboven.
> De allereerste keer dat u de app opent verschijnt vanzelf een
> welkom-scherm waar u dezelfde uitleg kunt openen.

---

## Inhoud

1. [Welkom](#1-welkom)
2. [De allereerste keer](#2-de-allereerste-keer)
3. [Mijn scanner instellen](#3-mijn-scanner-instellen)
   - [Canon PIXMA TS5150 (met klein scherm)](#31-canon-pixma-ts5150)
   - [Canon PIXMA TS3350 (zonder scherm)](#32-canon-pixma-ts3350)
   - [Eenvoudig alternatief: NAPS2](#33-eenvoudig-alternatief-naps2)
4. [Een boek scannen](#4-een-boek-scannen)
5. [Tekst bewerken](#5-tekst-bewerken)
6. [Handouts maken (PDF / Word / TXT)](#6-handouts-maken)
7. [Tips voor oude boeken](#7-tips-voor-oude-boeken)
8. [Probleemoplossing](#8-probleemoplossing)
9. [Waar staan mijn bestanden?](#9-waar-staan-mijn-bestanden)

---

## 1. Welkom

Met **BoekScanner** kunt u eenvoudig een boek inscannen en er
**handouts** van maken voor een cursus. De app maakt van de scans
automatisch **bewerkbare tekst** én nette **PDF- of Word-bestanden**.

Geen ervaring met computers nodig — volg de stappen in deze
handleiding één voor één.

---

## 2. De allereerste keer

Voordat u kunt beginnen moet de computer eenmalig wat kleine
programma's installeren die nodig zijn voor tekstherkenning (OCR
genoemd) en voor het maken van PDF-bestanden.

### Stap 1 — De installatie uitvoeren

1. Open de map waar BoekScanner staat (meestal op het bureaublad of
   in **Documenten**).
2. Open de map **`installer`**.
3. Klik met de **rechtermuisknop** op het bestand
   **`install_dependencies.ps1`**.
4. Kies **Uitvoeren met PowerShell**. Krijgt u de vraag of dit script
   veilig is? Klik op **Ja**.

> **⚠ Let op:** de installatie duurt **5 tot 10 minuten**. Er gebeurt
> veel op het scherm — dat hoort zo. Wacht tot u onderaan
> *"Klaar!"* ziet staan.

### Stap 2 — Controleren of alles goed is

1. Start BoekScanner door dubbel te klikken op **`BoekScanner.exe`**.
2. Kijk rechtsboven in de app:
   - 🟢 *"Tesseract … (4 talen)"* = alles goed!
   - 🔴 *"Tesseract niet gevonden"* = de installatie is niet helemaal
     gelukt. Probeer Stap 1 opnieuw, en doe nu een rechtermuisklik
     en kies **Als administrator uitvoeren**.

---

## 3. Mijn scanner instellen

Volg de stappen die bij **uw** scanner-model horen. U hoeft dit maar
**één keer** te doen.

### 3.1 Canon PIXMA TS5150

> **Herkennen:** kleine kleuren-LCD-scherm aan de voorkant.
> Werkt via USB-kabel of via wifi.

#### A. Scanner aansluiten op de computer

1. Sluit de stekker aan en zet de printer aan met de **AAN/UIT**-knop.
2. Open in een internetbrowser (Edge of Chrome) de pagina
   **<https://canon.com/ijsetup>** en typ daar in: **TS5150**.
3. Klik op **Download** en daarna op het gedownloade bestand om
   Canon's installatieprogramma te starten.
4. Volg de stappen op het scherm. Bij de vraag *"Welke verbinding?"*
   kunt u kiezen voor:
   - **USB** (kabel) — eenvoudigst, gebruik de meegeleverde kabel.
   - **Wifi** (draadloos) — handig als de printer niet bij de
     computer staat.
5. Vink bij de optie-keuze **"IJ Scan Utility"** aan. Dat programma
   heeft u zo nodig.

#### B. IJ Scan Utility koppelen aan BoekScanner

BoekScanner heeft een speciale map waar nieuwe scans automatisch in
terechtkomen. Die map heet de **"Scan inbox"**. Het pad ervan ziet u
links onder in de app, in het tipsblok.

1. Open **IJ Scan Utility** via Start-menu →
   *Canon Utilities* → *IJ Scan Utility*.
2. Klik onderin op **Settings…** (Instellingen).
3. Klik in de linkerbalk op **Document Scan**.
4. Bij **Save in** (Opslaan in) klikt u op het mapje-knopje en kiest u
   de **Scan inbox** van BoekScanner.

   > 💡 Het volledige pad ziet u in BoekScanner. Tip: u kunt het pad
   > selecteren en kopiëren met `Ctrl+C`, en daarna in IJ Scan
   > Utility plakken met `Ctrl+V`.

5. Bij **Data Format** (Bestandstype) kies **PNG** of **JPEG**.
6. Bij **Resolution** (Resolutie) kies **300 dpi** — dat is ideaal
   voor tekstherkenning.
7. Klik op **OK**.

#### C. Scannen vanaf nu

1. Leg de pagina met de tekst **naar beneden** op het scannerglas,
   in de hoek met het pijltje.
2. Sluit het deksel.
3. Open IJ Scan Utility en klik op **Document**.
4. De pagina wordt gescand en verschijnt automatisch in BoekScanner. ✓

### 3.2 Canon PIXMA TS3350

> **Herkennen:** **geen schermpje**, alleen wat kleine knopjes met
> lampjes. Scannen gaat **altijd via de computer**, niet via de
> printer zelf.

#### A. Scanner aansluiten op de computer

1. Sluit de stekker aan en zet de printer aan.
2. Sluit de printer met een **USB-kabel** aan op de computer (een
   gewone "USB-A naar USB-B" kabel).

   > 💡 Werkt USB niet? Dan kunt u ook wifi gebruiken. Druk op de
   > **knop met het wifi-symbool** en houd vast tot het oranje lampje
   > knippert. Volg dan de wifi-instructies op het Canon-installatie­
   > programma.

3. Open in een internetbrowser de pagina **<https://canon.com/ijsetup>**
   en typ daar in: **TS3350**.
4. Klik op **Download** en open het gedownloade bestand. Volg de
   stappen op het scherm.
5. Vink bij de optie-keuze **"IJ Scan Utility"** aan.

#### B. IJ Scan Utility koppelen aan BoekScanner

1. Open **IJ Scan Utility** via Start-menu →
   *Canon Utilities* → *IJ Scan Utility*.
2. Klik onderin op **Settings…** (Instellingen).
3. Klik in de linkerbalk op **Auto Scan**.
4. Bij **Save in** (Opslaan in) klikt u op het mapje-knopje en kiest u
   de **Scan inbox** van BoekScanner. Het pad ziet u in BoekScanner.
5. Bij **Data Format** kies **PNG**.
6. Bij **Resolution** kies **300 dpi**.
7. Klik op **OK**.

#### C. Scannen vanaf nu

1. Leg de pagina met de tekst **naar beneden** op het scannerglas,
   in de hoek met het pijltje.
2. Sluit het deksel.
3. Open IJ Scan Utility op de computer en klik op **Auto**.
4. De pagina wordt gescand en verschijnt automatisch in BoekScanner. ✓

> **⚠ Niet vanaf de printer scannen:** bij dit model heeft de
> "Scan"-knop op de printer geen effect, omdat er geen scherm is om
> de bestemming te kiezen. Altijd vanaf de computer starten.

### 3.3 Eenvoudig alternatief: NAPS2

Als IJ Scan Utility ingewikkeld blijkt, kunt u in plaats daarvan
**NAPS2** gebruiken — een gratis programma met één grote groene
**Scan**-knop. Werkt met beide Canon-modellen.

#### NAPS2 installeren

1. Ga naar **<https://www.naps2.com/>**.
2. Klik op **Download** en kies de Windows installer (`.exe`).
3. Open het gedownloade bestand en klik telkens op **Next** en
   **Install**.

#### NAPS2 instellen voor BoekScanner

1. Open **NAPS2**.
2. Klik op **Profiles** (Profielen) bovenaan, en dan op **New** (Nieuw).
3. Kies bij **Device** uw Canon-printer (TS5150 of TS3350).
4. Stel **Resolution: 300 dpi** in en **Color: Color**.
5. Klik op **OK**.
6. Ga nu naar het menu **Tools → Auto Save Settings**. Vink
   **Enable Auto Save** aan.
7. Bij **Output Path** kies de **Scan inbox** van BoekScanner.
8. Bij **File type** kies **PNG** of **JPEG**.
9. Vink ook aan: **Save each page as a separate file**.
10. Klik op **OK**.

Vanaf nu: leg een pagina op de scanner en klik op de grote groene
**Scan**-knop in NAPS2. De pagina komt vanzelf in BoekScanner terecht.

---

## 4. Een boek scannen

### Stap 1 — Een nieuw "boek" aanmaken

1. Klik bovenin op **＋ Nieuw boek**.
2. Geef het boek een naam, bijvoorbeeld
   *"Geschiedenis hoofdstuk 3"*.
3. Klik op **Aanmaken**.

Vanaf nu komt elke scan in dít boek terecht.

### Stap 2 — Pagina's scannen

Drie manieren om een pagina toe te voegen:

- **Met IJ Scan Utility of NAPS2** (zie hoofdstuk
  [§3](#3-mijn-scanner-instellen)): scan via de computer en de pagina
  komt automatisch in BoekScanner. ⭐ Aanbevolen.
- **Met de knop 📷 Scan nu** in BoekScanner zelf — werkt alleen als
  Windows uw scanner direct kan aansturen.
- **Bestaande PDF/foto's toevoegen**: sleep ze vanuit Verkenner
  direct in het venster, of klik op **📁 Bestanden toevoegen**.

### Stap 3 — Pagina-volgorde controleren

In de zijbalk links ziet u alle pagina's met kleine voorbeelden.
Klopt de volgorde niet? Sleep een pagina-tegel naar boven of beneden
om hem te verplaatsen.

---

## 5. Tekst bewerken

Op een pagina geklikt? Dan ziet u twee dingen:

- **Links**: de gescande pagina.
- **Rechts**: de tekst die de computer heeft herkend.
  **Deze tekst kunt u zelf wijzigen.**

### Knoppen

| Knop | Wat doet hij? |
|---|---|
| 💾 **Opslaan** | Slaat uw wijzigingen op. Wordt sowieso automatisch opgeslagen 1.5 seconde nadat u ophoudt met typen. |
| ✓ **Controleer spelling** | Geeft een lijst met mogelijk verkeerd gespelde woorden, met suggesties. |
| 🔄 **Opnieuw verwerken** | Doet de bewerking en tekstherkenning opnieuw. |
| 🗑️ **Verwijder** | Haalt deze pagina permanent weg. |

### Wat betekent het percentage?

Bovenaan de tekst staat *"OCR-zekerheid: 87%"* of vergelijkbaar.
Dit is hoe zeker de computer is dat hij de tekst goed gelezen heeft.

- 🟢 **85% of hoger**: bijna zeker correct.
- 🟠 **70 – 85%**: even nakijken kan geen kwaad.
- 🔴 **onder 70%**: grote kans op fouten — controleer de tekst.

---

## 6. Handouts maken

Onderin de app staat de export-balk.

### Welke formaten?

| Formaat | Wanneer? |
|---|---|
| 📕 **Doorzoekbare PDF** | Pagina's blijven er net als in het boek uit zien, maar u kunt erin **zoeken** en **kopiëren**. Beste voor digitale handouts. |
| 📘 **Word (.docx)** | Word-document met tekst én afbeeldingen. **Open in Word** om verder te bewerken. ⭐ Aanbevolen voor cursus-handouts. |
| 📄 **Platte tekst** | Alleen tekst, zonder opmaak. |
| 📝 **Markdown** | Voor websites of notities. |

### Eén bestand of per pagina?

- **Eén bestand met alle pagina's**: alles achter elkaar.
- **Ook per pagina**: elk bladzijde apart als los bestand.

### Hoe?

1. Vink onderaan aan welke formaten u wilt.
2. Vink aan of u één gecombineerd bestand of per pagina wilt
   (mag allebei).
3. Klik op **📤 Maak handouts**.
4. Even geduld — vooral PDF kost wat tijd. Daarna verschijnt
   rechtsonder een melding met **download-links**.

---

## 7. Tips voor oude boeken

- **Vergeeld papier**: BoekScanner past automatisch contrast en
  helderheid aan. Te flets? Klik op **🔄 Opnieuw verwerken**.
- **Twee pagina's tegelijk gescand** (opengeslagen boek): vink in
  de instellingen **"Twee-pagina splitter"** aan — de twee pagina's
  worden dan automatisch uit elkaar gehaald.
- **Krom en scheef**: BoekScanner zet scans automatisch recht.
- **Gotische letter** (oude Duitse drukletter):
  voer eenmalig uit:
  ```powershell
  installer\install_dependencies.ps1 -ExtraLanguages frk
  ```
  En vink "frk" aan in de instellingen.
- **Hele oude boekjes met dunne pagina's**: scan met een
  **donker stuk papier achter** de pagina, anders ziet u de
  achterkant erdoor heen.

---

## 8. Probleemoplossing

| Probleem | Oplossing |
|---|---|
| Rechtsboven staat 🔴 *Tesseract niet gevonden* | Installer opnieuw uitvoeren als administrator. |
| Knop **📷 Scan nu** doet niets | Uw scanner ondersteunt geen WIA. Gebruik IJ Scan Utility of NAPS2 (zie [§3](#3-mijn-scanner-instellen)). |
| Mijn scan komt niet automatisch in BoekScanner | Controleer dat het scan-programma écht naar de "Scan inbox"-map opslaat. En zorg dat een boek geopend is in BoekScanner. |
| OCR is helemaal verkeerd | Scan op **300 dpi** (niet hoger), zorg voor rechte plaatsing, klik op **🔄 Opnieuw verwerken**. |
| Doorzoekbare PDF lukt niet | Ghostscript ontbreekt. Voer de installer opnieuw uit, of installeer handmatig vanaf <https://www.ghostscript.com/releases/gsdnld.html>. |
| App start niet | Herstart Windows en probeer opnieuw. Werkt het niet, herhaal de installatie. **De map `data/` nooit weggooien — daar staan al uw boeken in.** |

---

## 9. Waar staan mijn bestanden?

Alles staat onder `data\` in de map waar BoekScanner draait:

```
data\
├── inbox\          <- scans wachten hier op import
└── projects\
    └── jouw-boek\
        ├── raw\        <- originele scans
        ├── processed\  <- bijgewerkte versies
        ├── thumbs\     <- kleine voorbeeldjes
        ├── ocr\        <- tekstbestanden per pagina
        ├── export\     <- uitvoer (PDF/DOCX/TXT/MD)
        └── project.json
```

> ⚠️ **Niets gaat naar internet** — alles blijft op uw eigen computer.
> Wilt u een back-up? Kopieer de hele `data\`-map naar een USB-stick.
