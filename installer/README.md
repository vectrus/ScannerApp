# Installer

## BoekScanner-Setup.exe

De aanbevolen distributie voor eindgebruikers is de installer uit GitHub
Releases: `BoekScanner-Setup.exe`.

De installer:

1. installeert BoekScanner in de gebruikersmap (`%LOCALAPPDATA%\Programs\BoekScanner`);
2. maakt een Startmenu-snelkoppeling;
3. kan optioneel een bureaubladsnelkoppeling maken;
4. start BoekScanner direct na installatie.

Build lokaal:

```powershell
# Eerst de app bouwen
.\installer\build.ps1 -SkipVenv

# Daarna, als Inno Setup is geinstalleerd:
iscc .\installer\BoekScanner.iss
```

Resultaat: `installer\output\BoekScanner-Setup.exe`.

Let op: zonder code-signing certificaat kan Windows SmartScreen nog steeds een
waarschuwing tonen. Een installer maakt installatie eenvoudiger, maar lost
reputatie/signing niet volledig op.

## install_dependencies.ps1

PowerShell-script dat de externe binaries installeert die BoekScanner
nodig heeft:

- **Tesseract OCR** (≥5.4) met taalbestanden voor Nederlands, Engels,
  Duits en Frans
- **Ghostscript** (voor doorzoekbare PDF-export via `ocrmypdf`)

### Gebruik

```powershell
# Open PowerShell ALS ADMINISTRATOR (rechtermuis → Als administrator)
cd C:\pad\naar\ScannerApp
Set-ExecutionPolicy -Scope Process Bypass -Force
.\installer\install_dependencies.ps1

# Optioneel: extra talen toevoegen
.\installer\install_dependencies.ps1 -ExtraLanguages frk,lat
# (frk = Fraktur voor oude Duitse drukletter, lat = Latijn)
```

Het script:
1. Probeert eerst `winget` (snel, modern Windows 10/11)
2. Valt terug op een directe download van de UB-Mannheim installer
3. Downloadt taalbestanden van [tesseract-ocr/tessdata_best](https://github.com/tesseract-ocr/tessdata_best)
4. Probeert Ghostscript via winget; geeft anders een handmatige
   download-link

### Waar komen de bestanden terecht?

- Tesseract: `C:\Program Files\Tesseract-OCR\` (incl. `tessdata\` map)
- Ghostscript: `C:\Program Files\gs\gsX.YY.Z\bin\`

BoekScanner detecteert deze paden automatisch via
`boekscanner.core.config.Config.resolve_tesseract` en `resolve_ghostscript`.
Je kunt ze handmatig overschrijven in `config.json`.
