<#
.SYNOPSIS
    Installeert de externe binaries waar BoekScanner van afhangt:
      - Tesseract OCR (incl. taalbestanden nld, eng, deu, fra)
      - Ghostscript (nodig voor doorzoekbare PDF via ocrmypdf)

.DESCRIPTION
    Probeert installatie via winget (modern Windows) en valt anders
    terug op directe download van de UB-Mannheim Tesseract installer.

    Werkt non-interactief; vraag desnoods aan de gebruiker om als
    admin te draaien voor systeem-wide installatie.

.EXAMPLE
    .\install_dependencies.ps1
    .\install_dependencies.ps1 -SkipTesseract
    .\install_dependencies.ps1 -ExtraLanguages frk,lat
#>

[CmdletBinding()]
param(
    [string[]] $Languages = @('nld','eng','deu','fra'),
    [string[]] $ExtraLanguages = @(),
    [switch]   $SkipTesseract,
    [switch]   $SkipGhostscript
)

$ErrorActionPreference = 'Stop'
$AllLanguages = $Languages + $ExtraLanguages | Select-Object -Unique

function Write-Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Test-Command($name) {
    $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Get-TesseractPath {
    $candidates = @(
        "$env:ProgramFiles\Tesseract-OCR\tesseract.exe",
        "${env:ProgramFiles(x86)}\Tesseract-OCR\tesseract.exe",
        "$env:LOCALAPPDATA\Programs\Tesseract-OCR\tesseract.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    if (Test-Command 'tesseract') { return (Get-Command 'tesseract').Source }
    return $null
}

function Install-TesseractViaWinget {
    if (-not (Test-Command 'winget')) {
        return $false
    }
    Write-Step "Tesseract installeren via winget..."
    try {
        winget install --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements
        return $true
    } catch {
        Write-Warning "winget install mislukt: $_"
        return $false
    }
}

function Install-TesseractDirect {
    Write-Step "Tesseract direct downloaden van UB-Mannheim..."
    $url  = 'https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe'
    $tmp  = Join-Path $env:TEMP 'tesseract-setup.exe'
    Write-Host "    Downloaden van $url ..."
    Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
    Write-Host "    Installer starten (UI verschijnt - accepteer alle defaults)..."
    Start-Process -FilePath $tmp -ArgumentList '/S' -Wait
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}

function Install-Tesseract {
    if (Get-TesseractPath) {
        Write-Host "Tesseract is al aanwezig: $(Get-TesseractPath)" -ForegroundColor Green
        return
    }
    if (-not (Install-TesseractViaWinget)) {
        Install-TesseractDirect
    }
    $exe = Get-TesseractPath
    if (-not $exe) {
        throw "Tesseract installatie mislukt. Installeer handmatig: https://github.com/UB-Mannheim/tesseract/wiki"
    }
    Write-Host "Tesseract OK: $exe" -ForegroundColor Green
}

function Get-AppRoot {
    # Het script woont in installer/ - de app-root is een niveau hoger.
    return (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

function Get-LocalTessdataDir {
    $root = Get-AppRoot
    $local = Join-Path $root 'data\tessdata'
    if (-not (Test-Path $local)) {
        New-Item -ItemType Directory -Force -Path $local | Out-Null
    }
    return $local
}

function Install-Languages {
    Write-Step "Taalbestanden controleren ($($AllLanguages -join ', '))..."
    $exe = Get-TesseractPath
    if (-not $exe) {
        Write-Warning "Tesseract niet gevonden - sla taalbestanden over."
        return
    }
    # We proberen ALTIJD eerst de lokale gebruikers-tessdata-map.
    # Daar zijn nooit admin-rechten voor nodig en BoekScanner herkent hem
    # via config.tessdata_dir (default ./data/tessdata).
    $tessdata = Get-LocalTessdataDir
    Write-Host "    Lokale tessdata-map (geen admin nodig): $tessdata" -ForegroundColor DarkGray
    # tessdata_fast = klein en snel; voor maximaal accurate (maar trage) OCR
    # kan men later handmatig tessdata_best plaatsen.
    $baseUrl = 'https://github.com/tesseract-ocr/tessdata_fast/raw/main'
    # 'osd' is de page-orientation/script detector en is altijd handig.
    $needed = @('osd') + $AllLanguages | Select-Object -Unique
    foreach ($lang in $needed) {
        $target = Join-Path $tessdata "$lang.traineddata"
        if (Test-Path $target) {
            $size = (Get-Item $target).Length
            Write-Host "    $lang.traineddata: al aanwezig ($size bytes)" -ForegroundColor DarkGray
            continue
        }
        $url = "$baseUrl/$lang.traineddata"
        Write-Host "    $lang.traineddata: downloaden..." -ForegroundColor Yellow
        try {
            Invoke-WebRequest -Uri $url -OutFile $target -UseBasicParsing
            $size = (Get-Item $target).Length
            Write-Host "    $lang.traineddata: OK ($size bytes)" -ForegroundColor Green
        } catch {
            Write-Warning "Kon $lang.traineddata niet downloaden: $_"
        }
    }
}

function Install-GhostscriptViaWinget {
    if (-not (Test-Command 'winget')) { return $false }
    Write-Step "Ghostscript installeren via winget..."
    try {
        winget install --id ArtifexSoftware.GhostScript --silent --accept-package-agreements --accept-source-agreements
        return $true
    } catch {
        Write-Warning "winget install mislukt: $_"
        return $false
    }
}

function Get-GhostscriptPath {
    $patterns = @(
        "$env:ProgramFiles\gs\gs*\bin\gswin64c.exe",
        "${env:ProgramFiles(x86)}\gs\gs*\bin\gswin64c.exe"
    )
    foreach ($p in $patterns) {
        $found = Get-ChildItem -Path $p -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

function Install-Ghostscript {
    $existing = Get-GhostscriptPath
    if ($existing) {
        Write-Host "Ghostscript al aanwezig: $existing" -ForegroundColor Green
        return
    }
    if (Install-GhostscriptViaWinget) {
        $found = Get-GhostscriptPath
        if ($found) {
            Write-Host "Ghostscript OK: $found" -ForegroundColor Green
            return
        }
    }
    Write-Warning @"
Ghostscript kon niet automatisch worden geinstalleerd.
Download het handmatig van https://www.ghostscript.com/releases/gsdnld.html
(64-bit versie) en installeer met de standaard-instellingen.
Doorzoekbare PDF-export werkt niet zonder Ghostscript.
"@
}

# ----- Hoofdscript ------------------------------------------------------

Write-Host "BoekScanner - afhankelijkheden installeren" -ForegroundColor Magenta
Write-Host "Talen: $($AllLanguages -join ', ')"

if (-not $SkipTesseract) {
    Install-Tesseract
    Install-Languages
} else {
    Write-Host "Tesseract overgeslagen (--SkipTesseract)" -ForegroundColor Yellow
}

if (-not $SkipGhostscript) {
    Install-Ghostscript
} else {
    Write-Host "Ghostscript overgeslagen (--SkipGhostscript)" -ForegroundColor Yellow
}

Write-Step "Klaar!"
$ts = Get-TesseractPath
$gs = Get-GhostscriptPath
$localTd = Join-Path (Get-AppRoot) 'data\tessdata'
if ($ts)               { Write-Host "  Tesseract:    $ts" -ForegroundColor Green }
if ($gs)               { Write-Host "  Ghostscript:  $gs" -ForegroundColor Green }
if (Test-Path $localTd) {
    $count = (Get-ChildItem $localTd -Filter '*.traineddata' -ErrorAction SilentlyContinue).Count
    if ($count -gt 0) {
        Write-Host "  Taalpakketten: $count bestanden in $localTd" -ForegroundColor Green
    }
}
Write-Host ""
Write-Host "Je kunt nu BoekScanner starten." -ForegroundColor Magenta
