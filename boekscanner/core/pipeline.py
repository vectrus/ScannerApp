"""Per-pagina pipeline: afbeelding → bewerking → OCR → opslag in project.

Behandelt één ruwe pagina (PageMeta die net is toegevoegd) en doet:

1. Afbeelding inladen (uit raw/) — converteer PDF eerste-pagina indien nodig.
2. Image-processing (deskew + crop + enhance + optionele two-page split).
3. Schrijf bewerkte versie naar processed/.
4. Genereer thumbnail naar thumbs/.
5. OCR de bewerkte versie en sla tekst op naar ocr/.
6. Update PageMeta met alle info.

Bij een two-page split wordt de oorspronkelijke pagina vervangen door 2
nieuwe pagina-records.
"""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
from loguru import logger

from . import image_proc as ip
from .config import get_config
from .ocr import ocr_image
from .projects import PageMeta, Project


@dataclass
class PageProcessingResult:
    project: Project
    new_pages: List[PageMeta]


def _pdf_first_page_to_image(pdf_path: Path, dpi: int = 300) -> Optional[Path]:
    """Converteer eerste pagina van een PDF naar PNG (ad-hoc tijdelijk bestand).

    Gebruikt PyMuPDF als beschikbaar; valt anders terug op ``pdf2image``
    (die Poppler vereist). Geeft ``None`` terug als geen van beide werkt.
    """
    try:
        import pymupdf  # type: ignore
        doc = pymupdf.open(pdf_path)
        if doc.page_count == 0:
            return None
        page = doc.load_page(0)
        zoom = dpi / 72
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        out_path = pdf_path.with_suffix(".converted.png")
        pix.save(str(out_path))
        return out_path
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("PyMuPDF kon PDF niet renderen: {}", exc)

    try:
        from pdf2image import convert_from_path  # type: ignore
        images = convert_from_path(str(pdf_path), dpi=dpi, first_page=1, last_page=1)
        if not images:
            return None
        out_path = pdf_path.with_suffix(".converted.png")
        images[0].save(str(out_path), "PNG")
        return out_path
    except Exception as exc:
        logger.warning("Kan PDF niet renderen voor preview/OCR: {}", exc)
        return None


def process_new_page(
    project: Project,
    page: PageMeta,
    *,
    run_ocr: bool = True,
    overrides: Optional[ip.ProcessingOptions] = None,
) -> PageProcessingResult:
    """Doorloop de volledige pipeline voor één (net geïmporteerde) pagina."""
    raw_path = project.raw_dir / page.raw_filename
    if not raw_path.is_file():
        raise FileNotFoundError(raw_path)

    if raw_path.suffix.lower() == ".pdf":
        rendered = _pdf_first_page_to_image(raw_path)
        if rendered is None:
            raise RuntimeError(
                "Kan PDF niet renderen — installeer 'pymupdf' of 'pdf2image+poppler'."
            )
        img = ip.load_image(rendered)
        # Tijdelijk bestand kan blijven bestaan; we gebruiken het voor processed/
    else:
        img = ip.load_image(raw_path)

    options = overrides or project.meta.settings.to_processing_options()
    processed_pieces = ip.process_page(img, options)

    new_pages: List[PageMeta] = []
    if len(processed_pieces) == 1:
        # Update bestaande pagina-meta
        new_pages.append(_finalize_piece(project, page, processed_pieces[0], run_ocr))
    else:
        # Split: vervang oorspronkelijke pagina door 1..N nieuwe
        # Verwijder eerst de oude page uit meta (raw/ blijft staan, we hergebruiken het)
        original_index = next(
            i for i, p in enumerate(project.meta.pages) if p.id == page.id
        )
        project.meta.pages.pop(original_index)
        for offset, piece in enumerate(processed_pieces):
            piece_id = uuid.uuid4().hex[:12]
            piece_meta = PageMeta(id=piece_id, raw_filename=page.raw_filename)
            project.meta.pages.insert(original_index + offset, piece_meta)
            new_pages.append(_finalize_piece(project, piece_meta, piece, run_ocr))
        project.save()

    return PageProcessingResult(project=project, new_pages=new_pages)


def _finalize_piece(
    project: Project,
    page: PageMeta,
    processed_img,
    run_ocr: bool,
) -> PageMeta:
    """Schrijf processed/, thumb/, evt OCR voor één afbeelding-piece."""
    page.height, page.width = processed_img.shape[:2]

    processed_name = f"{page.id}.png"
    processed_path = project.processed_dir / processed_name
    ip.save_image(processed_img, processed_path)
    page.processed_filename = processed_name

    thumb = ip.make_thumbnail(processed_img, max_side=240)
    thumb_name = f"{page.id}.jpg"
    ip.save_image(thumb, project.thumbs_dir / thumb_name, quality=80)
    page.thumb_filename = thumb_name

    if run_ocr:
        try:
            result = ocr_image(
                processed_img,
                languages=project.meta.settings.languages,
                psm=project.meta.settings.psm,
            )
            project.save_ocr_text(page.id, result.text, result.avg_confidence)
            # save_ocr_text update text_preview/avg_confidence/ocr_filename intern
            return project.get_page(page.id)
        except Exception as exc:
            logger.error("OCR voor pagina {} mislukt: {}", page.id, exc)

    project.update_page(page)
    return page
