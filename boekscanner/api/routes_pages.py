"""Endpoints voor pagina's binnen een project: upload, OCR-tekst lezen/wijzigen,
herverwerken, beelden serveren en spellcheck.
"""

from __future__ import annotations

import io
import shutil
import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from ..core import image_proc as ip
from ..core.pipeline import process_new_page
from ..core.spellcheck import check_text
from ..core.projects import ProjectMeta
from .schemas import (
    PageOut,
    ReorderPagesIn,
    ReprocessIn,
    SpellSuggestionOut,
    UpdateOcrIn,
)
from .state import get_state


router = APIRouter(prefix="/api/pages", tags=["pages"])


def _project_or_404():
    state = get_state()
    if state.active_project is None:
        raise HTTPException(status_code=400, detail="Geen actief project geopend.")
    return state.active_project


def _page_to_out(meta: ProjectMeta, page_id: str) -> PageOut:
    project = _project_or_404()
    for i, p in enumerate(project.meta.pages):
        if p.id == page_id:
            return PageOut(
                id=p.id,
                index=i + 1,
                width=p.width,
                height=p.height,
                has_processed=bool(p.processed_filename),
                has_thumb=bool(p.thumb_filename),
                has_ocr=bool(p.ocr_filename),
                text_preview=p.text_preview,
                avg_confidence=p.avg_confidence,
                rotation_degrees=p.rotation_degrees,
                created_at=p.created_at,
            )
    raise HTTPException(status_code=404, detail="Pagina niet gevonden.")


# --- Upload (drag & drop) --------------------------------------------------


@router.post("/upload", response_model=List[PageOut])
async def upload_pages(files: List[UploadFile] = File(...)):
    project = _project_or_404()
    out: List[PageOut] = []
    for f in files:
        if f.filename is None:
            continue
        suffix = Path(f.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(f.file, tmp)
            tmp_path = Path(tmp.name)
        try:
            page = project.add_page_from_file(tmp_path, copy=False)
            process_new_page(project, page, run_ocr=True)
            # Page-list kan veranderd zijn (split); pak de laatste toegevoegde
            for p in project.meta.pages:
                if p.id == page.id or p.raw_filename == page.raw_filename:
                    out.append(_page_to_out(project.meta, p.id))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    return out


# --- Volgorde --------------------------------------------------------------


@router.post("/reorder", status_code=204)
def reorder_pages(payload: ReorderPagesIn):
    project = _project_or_404()
    try:
        project.reorder_pages(payload.page_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return None


# --- Verwijderen -----------------------------------------------------------


@router.delete("/{page_id}", status_code=204)
def delete_page(page_id: str):
    project = _project_or_404()
    try:
        project.delete_page(page_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None


# --- OCR-tekst lezen/wijzigen ---------------------------------------------


@router.get("/{page_id}/text", response_class=PlainTextResponse)
def get_page_text(page_id: str):
    project = _project_or_404()
    try:
        page = project.get_page(page_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if not page.ocr_filename:
        return ""
    return (project.ocr_dir / page.ocr_filename).read_text(encoding="utf-8")


@router.put("/{page_id}/text", response_model=PageOut)
def update_page_text(page_id: str, payload: UpdateOcrIn):
    project = _project_or_404()
    try:
        page = project.get_page(page_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    project.save_ocr_text(page_id, payload.text, page.avg_confidence or 0.0)
    return _page_to_out(project.meta, page_id)


# --- Reprocess (her-verwerken / opnieuw OCR) ------------------------------


@router.post("/{page_id}/reprocess", response_model=List[PageOut])
def reprocess_page(page_id: str, payload: ReprocessIn):
    project = _project_or_404()
    try:
        page = project.get_page(page_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if payload.rotation_degrees is not None:
        if payload.rotation_degrees % 90 != 0:
            raise HTTPException(status_code=400, detail="Rotatie moet 0, 90, 180 of 270 graden zijn.")
        page.rotation_degrees = payload.rotation_degrees % 360

    base = project.meta.settings.to_processing_options()
    overrides = ip.ProcessingOptions(
        deskew=payload.deskew if payload.deskew is not None else base.deskew,
        crop=payload.crop if payload.crop is not None else base.crop,
        enhance=payload.enhance if payload.enhance is not None else base.enhance,
        split_pages=payload.split_pages if payload.split_pages is not None else base.split_pages,
        force_split=payload.force_split,
        rotation_degrees=page.rotation_degrees,
    )
    result = process_new_page(project, page, run_ocr=payload.rerun_ocr, overrides=overrides)
    return [_page_to_out(project.meta, p.id) for p in result.new_pages]


# --- Beelden serveren -----------------------------------------------------


@router.get("/{page_id}/thumb")
def get_thumb(page_id: str):
    project = _project_or_404()
    try:
        page = project.get_page(page_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if not page.thumb_filename:
        raise HTTPException(status_code=404, detail="Geen thumbnail.")
    return FileResponse(project.thumbs_dir / page.thumb_filename, media_type="image/jpeg")


@router.get("/{page_id}/image")
def get_image(page_id: str, processed: bool = True):
    project = _project_or_404()
    try:
        page = project.get_page(page_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if processed and page.processed_filename:
        path = project.processed_dir / page.processed_filename
    else:
        path = project.raw_dir / page.raw_filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Beeld niet gevonden.")
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    if path.suffix.lower() == ".pdf":
        media = "application/pdf"
    return FileResponse(path, media_type=media)


# --- Spellcheck -----------------------------------------------------------


@router.get("/{page_id}/spellcheck", response_model=List[SpellSuggestionOut])
def spellcheck_page(page_id: str, language: str = "nl-NL"):
    project = _project_or_404()
    try:
        page = project.get_page(page_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if not page.ocr_filename:
        return []
    text = (project.ocr_dir / page.ocr_filename).read_text(encoding="utf-8")
    suggestions = check_text(text, language=language)
    return [SpellSuggestionOut(**s.__dict__) for s in suggestions]
