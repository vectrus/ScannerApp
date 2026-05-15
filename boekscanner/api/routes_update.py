"""Update endpoints."""

from __future__ import annotations

import os
import threading
from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from ..core.updater import check_for_update, download_update, launch_update_script, prepare_update

router = APIRouter(prefix="/api/update", tags=["update"])


@router.get("/check")
def check_update() -> dict:
    """Check GitHub Releases for a newer BoekScanner build."""
    return asdict(check_for_update())


@router.post("/install")
def install_update() -> dict:
    """Download latest release zip, prepare updater script, then restart app."""
    check = check_for_update()
    if not check.available:
        raise HTTPException(status_code=400, detail=check.message or "Geen update beschikbaar.")
    try:
        zip_path = download_update()
        script_path = prepare_update(zip_path)
        launch_update_script(script_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Give the HTTP response a moment to reach the browser, then exit. The
    # updater PowerShell script is already waiting for this PID to stop.
    threading.Timer(1.0, lambda: os._exit(0)).start()
    return {"message": "Update wordt geïnstalleerd. BoekScanner start zo opnieuw."}
