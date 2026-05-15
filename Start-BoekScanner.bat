@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo BoekScanner kan niet starten: .venv\Scripts\python.exe is niet gevonden.
  echo.
  echo Open PowerShell in deze map en voer eerst uit:
  echo   py -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements-test.txt
  echo.
  pause
  exit /b 1
)

echo.
echo BoekScanner wordt gestart...
echo Als de browser niet vanzelf opent, ga naar:
echo   http://127.0.0.1:8765
echo.

".venv\Scripts\python.exe" run.py --dev

echo.
echo BoekScanner is gestopt.
pause
