"""Endpoints voor het exporteren van een project en het downloaden van resultaten."""

from __future__ import annotations

from pathlib import Path
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..core import exports as ex
from .schemas import ExportFileOut, ExportIn, ExportResponseOut
from .state import get_state


router = APIRouter(prefix="/api/export", tags=["export"])


def _to_file_out(slug: str, fmt: str, p: Path, label_prefix: str = "") -> ExportFileOut:
    rel = p.name
    return ExportFileOut(
        label=f"{label_prefix}{p.name}",
        download_url=f"/api/export/{slug}/{fmt}/{quote(rel)}",
        size_bytes=p.stat().st_size,
    )


@router.post("", response_model=ExportResponseOut)
def export_project(payload: ExportIn):
    state = get_state()
    if state.active_project is None:
        raise HTTPException(status_code=400, detail="Geen actief project.")
    project = state.active_project

    # Validatie
    valid = {"pdf", "docx", "txt", "md"}
    bad = [f for f in payload.formats if f not in valid]
    if bad:
        raise HTTPException(status_code=400, detail=f"Onbekende formaten: {bad}")

    files: List[ExportFileOut] = []
    try:
        results = ex.export_project(
            project,
            formats=payload.formats,  # type: ignore[arg-type]
            per_page=payload.per_page,
            combined=payload.combined,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    for r in results:
        if r.combined_path:
            files.append(_to_file_out(project.meta.slug, r.format, r.combined_path, "📚 "))
        for p in r.per_page_paths:
            files.append(_to_file_out(project.meta.slug, r.format, p, "📄 "))

    return ExportResponseOut(files=files)


@router.get("/{slug}/{fmt}/{filename}")
def download_export(slug: str, fmt: str, filename: str):
    state = get_state()
    try:
        project = state.manager.open(slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    target = (project.export_dir / fmt / filename).resolve()
    # Beveiliging: target moet binnen de export-map blijven
    base = project.export_dir.resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ongeldig pad.")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Bestand niet gevonden.")

    media_map = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
    }
    return FileResponse(
        target,
        media_type=media_map.get(fmt, "application/octet-stream"),
        filename=target.name,
    )
