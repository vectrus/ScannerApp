# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec voor BoekScanner.

Bouwen vanuit project-root:
    pyinstaller installer/BoekScanner.spec

Resultaat: dist/BoekScanner/BoekScanner.exe (one-folder bundle)
of dist/BoekScanner.exe (one-file) — afhankelijk van ONE_FILE flag.
"""

from pathlib import Path

import PyInstaller.config
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ONE_FILE = False  # one-folder is sneller op te starten en makkelijker te debuggen

ROOT = Path(SPECPATH).resolve().parent  # installer/ -> project-root

# Bundle de complete web/ map (HTML/CSS/JS) en de installer/-map
datas = [
    (str(ROOT / "boekscanner" / "web"), "boekscanner/web"),
    (str(ROOT / "installer" / "install_dependencies.ps1"), "installer"),
    (str(ROOT / "HANDLEIDING.md"), "."),
    (str(ROOT / "config.example.json"), "."),
    (str(ROOT / "README.md"), "."),
]

# Verzamel data-files voor pakketten die runtime-resources nodig hebben
for pkg in ("ocrmypdf", "pikepdf", "pymupdf", "language_tool_python"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

hiddenimports = []
for pkg in ("pytesseract", "ocrmypdf", "ocrmypdf.builtin_plugins", "pikepdf", "pymupdf",
            "language_tool_python", "watchdog.observers", "uvicorn.logging",
            "uvicorn.loops", "uvicorn.loops.auto", "uvicorn.protocols",
            "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
            "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
            "uvicorn.lifespan", "uvicorn.lifespan.on"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        hiddenimports.append(pkg)

block_cipher = None

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=list(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if ONE_FILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="BoekScanner",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "installer" / "icon.ico") if (ROOT / "installer" / "icon.ico").is_file() else None,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="BoekScanner",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        icon=str(ROOT / "installer" / "icon.ico") if (ROOT / "installer" / "icon.ico").is_file() else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="BoekScanner",
    )
