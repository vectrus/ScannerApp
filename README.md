# BoekScanner

Een eenvoudige Windows-app om boeken pagina-voor-pagina te scannen met een
Canon all-in-one printer/scanner, automatisch te OCR'en (Nederlands, Engels,
Duits, Frans), en te exporteren naar **doorzoekbare PDF**, **Word (.docx)**
of **platte tekst** — per pagina én als één gecombineerd document.

Speciaal ontworpen voor het scannen van **oudere boeken** voor
cursus-handouts, met automatische bijsnijden, rechtzetten en
beeldverbetering voor vergeeld papier.

## Functies

- 🔘 **Drie scan-manieren**:
  1. **Folder-watcher** — laat NAPS2 of Canon's eigen software in de
     "Scan inbox" map dumpen, BoekScanner pikt scans automatisch op.
  2. **Drag & drop** — sleep losse PDF/JPG/PNG bestanden in de app.
  3. **Scan nu-knop** — direct scannen via Windows WIA (werkt met de
     meeste Canon-modellen).
- 📚 **Boek-projecten** — elke scan-sessie is een "boek" met eigen mapje
  en automatische paginavolgorde.
- ✨ **Beeldverbetering**:
  - Auto-deskew (rechtzetten van scheve scans)
  - Auto-crop (witruimte rondom wegsnijden)
  - Twee-pagina splitter (opengeslagen boek → twee aparte pagina's)
  - Contrast/helderheid optimalisatie voor vergeeld papier
- 🔤 **OCR met Tesseract**: Nederlands, Engels, Duits, Frans (en optioneel
  Fraktur voor pre-1900 Duitse boeken).
- ✏️ **Live preview & bewerkbare OCR-tekst** naast de scan.
- ✅ **Nederlandse spellingscontrole** voor snelle correctie.
- 📤 **Export naar**:
  - Doorzoekbare PDF (originele scan + onzichtbare tekstlaag)
  - Word `.docx` per pagina én als geheel
  - Platte tekst `.txt` en Markdown `.md`

## Voor wie?

Voor mensen die **geen** Python, Docker of terminal willen aanraken.
Eindgebruikers krijgen één `.exe`-bestand. Dubbelklikken en gaan.

## Installatie (eindgebruiker)

1. Download `BoekScanner-Setup.exe` uit de GitHub Releases-pagina.
2. Dubbelklik op `BoekScanner-Setup.exe`.
3. Volg de stappen op het scherm. De installer zet BoekScanner in uw gebruikersmap en maakt een Startmenu-snelkoppeling.
4. Start `BoekScanner` vanuit het Startmenu. De app regelt daarna:
   - Tesseract OCR met Nederlandse, Engelse, Duitse en Franse
     taalbestanden
   - Ghostscript (nodig voor doorzoekbare PDF's)
   - De BoekScanner-app zelf

## Updates voor eindgebruikers

BoekScanner heeft een **Update**-knop rechtsboven. Die controleert de nieuwste
GitHub Release en downloadt `BoekScanner-windows.zip` voor de interne app-update.
Daarna sluit de app zichzelf, vervangt alleen de appbestanden, en start opnieuw.

Belangrijk: de map `data/` en `config.json` worden niet vervangen. Gescande
boeken en lokale instellingen blijven dus staan.

Voor automatische updates moet `config.json` of `config.example.json` deze
waarden bevatten:

```json
"updates": {
  "enabled": true,
  "github_owner": "vectrus",
  "github_repo": "ScannerApp",
  "asset_name": "BoekScanner-windows.zip"
}
```

## Releases maken

Elke push of merge naar `main` draait `.github/workflows/release-windows.yml`.
Die workflow:

1. bouwt de Windows-app met PyInstaller;
2. zet een unieke build-id in `boekscanner/build_info.py`;
3. maakt `BoekScanner-windows.zip`;
4. maakt daarnaast `BoekScanner-Setup.exe` met Inno Setup;
5. publiceert de zip en installer als nieuwste GitHub Release.

Nieuwe gebruikers downloaden de installer. Bestaande gebruikers hoeven daarna
alleen in BoekScanner op **Update** te klikken.

## Voor ontwikkelaars

```powershell
# Python 3.11+ vereist
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Tesseract handmatig installeren (zie installer/install_dependencies.ps1)
.\installer\install_dependencies.ps1

# App starten in development-modus (browser-UI op http://127.0.0.1:8765)
python run.py --dev

# App starten als desktop-window (PyWebView)
python run.py
```

## Mappenstructuur

```
ScannerApp/
├── boekscanner/            # Python package
│   ├── api/                # FastAPI endpoints
│   ├── core/               # OCR, image-processing, exports, watcher
│   ├── web/                # HTML/CSS/JS frontend
│   └── main.py             # PyWebView entry-point
├── installer/              # PowerShell installer-scripts
├── tests/                  # Unit-tests
├── data/                   # Lokale opslag van boeken (gitignore)
│   ├── inbox/              # Scan-inbox (folder-watcher)
│   └── projects/           # Per-boek mapjes
├── requirements.txt
├── config.example.json
└── run.py
```

## Licentie

MIT — zie `LICENSE`.
