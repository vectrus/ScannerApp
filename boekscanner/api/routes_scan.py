"""Endpoints voor direct scannen via WIA en het ophalen van scanner-info."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ..core import wia_scan
from .schemas import PageOut, ScanRequestIn, ScannerOut
from .state import get_state


router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.get("/scanners", response_model=List[ScannerOut])
def list_scanners():
    try:
        scanners = wia_scan.list_scanners()
    except wia_scan.WiaError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return [ScannerOut(**s.__dict__) for s in scanners]


@router.post("", response_model=List[PageOut])
def scan_now(payload: ScanRequestIn):
    """Scan één pagina via WIA → komt in de inbox → watcher importeert het.

    Geeft de geüpdatete pagina-lijst terug nadat de scan is verwerkt.
    """
    state = get_state()
    if state.active_project is None:
        raise HTTPException(
            status_code=400,
            detail="Open of maak eerst een project voordat je scant.",
        )
    try:
        wia_scan.scan_to_inbox(
            device_id=payload.device_id,
            dpi=payload.dpi,
            color=payload.color,  # type: ignore[arg-type]
            output_format=payload.output_format,  # type: ignore[arg-type]
        )
    except wia_scan.WiaError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    # De watcher pikt het op (kan even duren). De UI poll'd /api/projects/active.
    project = state.manager.open(state.active_project.meta.slug)
    state.set_active(project)
    return [
        PageOut(
            id=p.id,
            index=i + 1,
            width=p.width,
            height=p.height,
            has_processed=bool(p.processed_filename),
            has_thumb=bool(p.thumb_filename),
            has_ocr=bool(p.ocr_filename),
            text_preview=p.text_preview,
            avg_confidence=p.avg_confidence,
            created_at=p.created_at,
        )
        for i, p in enumerate(project.meta.pages)
    ]
