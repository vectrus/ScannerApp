<#
.SYNOPSIS
    Build BoekScanner als one-folder Windows-applicatie via PyInstaller.

.DESCRIPTION
    1. Maakt een tijdelijke virtual environment.
    2. Installeert requirements.txt + PyInstaller.
    3. Roept `pyinstaller` aan met onze spec.
    4. Resultaat staat in `dist/BoekScanner/` en is direct draaibaar
       door dubbel te klikken op `BoekScanner.exe`.

    De resulterende map kan vervolgens via een NSIS- of Inno-Setup
    installer gepackaged worden, of als ZIP gedeeld worden.

.EXAMPLE
    .\installer\build.ps1
#>

[CmdletBinding()]
param(
    [string] $PythonExe = 'py',
    [switch] $SkipVenv
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "BoekScanner build" -ForegroundColor Magenta
Write-Host "Project: $ProjectRoot"

# Virtual env aanmaken
$venv = Join-Path $ProjectRoot '.build-venv'
if (-not $SkipVenv) {
    if (Test-Path $venv) {
        Write-Host "Bestaande build-venv verwijderen..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $venv
    }
    Write-Host "Build-venv aanmaken in $venv ..." -ForegroundColor Cyan
    & $PythonExe -m venv $venv
}
$python = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw "Python niet gevonden in venv: $python"
}

Write-Host "Pip upgraden..." -ForegroundColor Cyan
& $python -m pip install --upgrade pip wheel setuptools

Write-Host "Requirements installeren..." -ForegroundColor Cyan
& $python -m pip install -r (Join-Path $ProjectRoot 'requirements.txt')

Write-Host "PyInstaller-build starten..." -ForegroundColor Cyan
& $python -m PyInstaller --noconfirm (Join-Path $PSScriptRoot 'BoekScanner.spec')

$dist = Join-Path $ProjectRoot 'dist\BoekScanner'
if (-not (Test-Path $dist)) {
    throw "Build mislukt — dist-map ontbreekt."
}

Write-Host ""
Write-Host "Klaar!" -ForegroundColor Green
Write-Host "  $dist" -ForegroundColor Green
Write-Host ""
Write-Host "Test door dubbel-klik op BoekScanner.exe in $dist"
