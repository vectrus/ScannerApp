"""Korte wrapper-script om BoekScanner te starten in development.

Gebruik:
    python run.py            # Desktop-window (PyWebView)
    python run.py --dev      # Browser + auto-reload
    python run.py --no-window  # Alleen server (debug)
"""

from __future__ import annotations

import sys

from boekscanner.main import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
