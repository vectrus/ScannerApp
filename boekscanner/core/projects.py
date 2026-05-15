"""Boek-project beheer.

Een 'project' is één boek dat je scant. Per project bestaat er een mapje
onder ``data/projects/<slug>/`` met:

::

    raw/         — originele scans (PDF, JPG, PNG)
    processed/   — bewerkte versies (deskew/crop/enhance)
    thumbs/      — kleine voorvertoningen voor de UI
    ocr/         — geëxtraheerde tekst per pagina (.txt)
    export/      — eind-bestanden (PDF, DOCX, MD, TXT, ZIP)
    project.json — metadata, paginavolgorde, instellingen

De ``Page``-objecten worden in een lijst bewaard; index in die lijst is de
weergegeven paginanummer (1-based in de UI). Bestanden zelf zijn benoemd
met een UUID zodat hernummeren goedkoop is (alleen ``project.json``
hoeft te wijzigen).
"""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel, Field
from slugify import slugify

from .config import get_config
from .image_proc import ProcessingOptions


PROJECT_FILE = "project.json"
SUBDIRS = ("raw", "processed", "thumbs", "ocr", "export")
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
ALLOWED_PDF_EXT = {".pdf"}


# --- Modellen --------------------------------------------------------------


class PageMeta(BaseModel):
    id: str
    raw_filename: str
    processed_filename: Optional[str] = None
    thumb_filename: Optional[str] = None
    ocr_filename: Optional[str] = None
    text_preview: Optional[str] = None  # eerste ~80 tekens voor sidebar
    avg_confidence: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    rotation_degrees: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ProjectSettings(BaseModel):
    languages: List[str] = Field(default_factory=lambda: ["nld", "eng", "deu", "fra"])
    psm: int = 3
    auto_deskew: bool = True
    auto_crop: bool = True
    auto_enhance_old_paper: bool = True
    two_page_split: bool = False
    spellcheck_enabled: bool = True

    def to_processing_options(self) -> ProcessingOptions:
        return ProcessingOptions(
            deskew=self.auto_deskew,
            crop=self.auto_crop,
            enhance=self.auto_enhance_old_paper,
            split_pages=self.two_page_split,
        )


class ProjectMeta(BaseModel):
    slug: str
    name: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    description: str = ""
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    pages: List[PageMeta] = Field(default_factory=list)


# --- Project-object --------------------------------------------------------


@dataclass
class Project:
    """Hoog-niveau wrapper rond een project-mapje."""

    meta: ProjectMeta
    root: Path

    # ---- mappen-helpers ----

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.root / "processed"

    @property
    def thumbs_dir(self) -> Path:
        return self.root / "thumbs"

    @property
    def ocr_dir(self) -> Path:
        return self.root / "ocr"

    @property
    def export_dir(self) -> Path:
        return self.root / "export"

    @property
    def project_file(self) -> Path:
        return self.root / PROJECT_FILE

    # ---- persistentie ----

    def save(self) -> None:
        self.meta.updated_at = datetime.utcnow().isoformat()
        self.project_file.write_text(
            self.meta.model_dump_json(indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, root: Path) -> "Project":
        data = json.loads((root / PROJECT_FILE).read_text(encoding="utf-8"))
        return cls(meta=ProjectMeta(**data), root=root)

    # ---- paginabeheer ----

    def add_page_from_file(self, source: Path, copy: bool = True) -> PageMeta:
        """Importeer één bestand als een nieuwe ruwe pagina.

        ``copy=True`` (default) kopieert; ``False`` verplaatst (handig voor
        de inbox-watcher, die het bestand uit de inbox wil halen).
        """
        if not source.is_file():
            raise FileNotFoundError(source)
        ext = source.suffix.lower()
        if ext not in ALLOWED_IMAGE_EXT and ext not in ALLOWED_PDF_EXT:
            raise ValueError(f"Niet-ondersteund bestandstype: {ext}")
        page_id = uuid.uuid4().hex[:12]
        target_name = f"{page_id}{ext}"
        target = self.raw_dir / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if copy:
            shutil.copy2(source, target)
        else:
            shutil.move(str(source), str(target))
        page = PageMeta(id=page_id, raw_filename=target_name)
        self.meta.pages.append(page)
        self.save()
        logger.info("Pagina toegevoegd aan project '{}': {}", self.meta.slug, target_name)
        return page

    def get_page(self, page_id: str) -> PageMeta:
        for p in self.meta.pages:
            if p.id == page_id:
                return p
        raise KeyError(f"Pagina niet gevonden: {page_id}")

    def update_page(self, page: PageMeta) -> None:
        for i, p in enumerate(self.meta.pages):
            if p.id == page.id:
                self.meta.pages[i] = page
                self.save()
                return
        raise KeyError(f"Pagina niet gevonden: {page.id}")

    def reorder_pages(self, ordered_ids: List[str]) -> None:
        """Pas paginavolgorde aan op basis van een lijst id's."""
        by_id = {p.id: p for p in self.meta.pages}
        if set(ordered_ids) != set(by_id.keys()):
            raise ValueError("Reorder-lijst komt niet overeen met bestaande pagina-ids.")
        self.meta.pages = [by_id[i] for i in ordered_ids]
        self.save()

    def delete_page(self, page_id: str) -> None:
        page = self.get_page(page_id)
        for sub, name in (
            (self.raw_dir, page.raw_filename),
            (self.processed_dir, page.processed_filename),
            (self.thumbs_dir, page.thumb_filename),
            (self.ocr_dir, page.ocr_filename),
        ):
            if name:
                fp = sub / name
                if fp.is_file():
                    fp.unlink()
        self.meta.pages = [p for p in self.meta.pages if p.id != page_id]
        self.save()

    def save_ocr_text(self, page_id: str, text: str, avg_conf: float) -> None:
        page = self.get_page(page_id)
        ocr_name = f"{page_id}.txt"
        (self.ocr_dir / ocr_name).write_text(text, encoding="utf-8")
        page.ocr_filename = ocr_name
        page.avg_confidence = avg_conf
        page.text_preview = (text[:80] + "…") if len(text) > 80 else text
        self.update_page(page)


# --- Manager ---------------------------------------------------------------


class ProjectManager:
    """Beheert alle projecten in ``data/projects``."""

    def __init__(self) -> None:
        self.cfg = get_config()
        self.root = self.cfg.projects_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> List[ProjectMeta]:
        out: List[ProjectMeta] = []
        for child in sorted(self.root.iterdir()):
            pf = child / PROJECT_FILE
            if pf.is_file():
                try:
                    out.append(ProjectMeta(**json.loads(pf.read_text(encoding="utf-8"))))
                except Exception as exc:
                    logger.warning("Beschadigd project overgeslagen ({}): {}", child, exc)
        return out

    def create(self, name: str, description: str = "") -> Project:
        slug = slugify(name) or uuid.uuid4().hex[:8]
        # Voorkom collisions
        base_slug = slug
        suffix = 1
        while (self.root / slug).exists():
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        project_root = self.root / slug
        project_root.mkdir(parents=True)
        for sub in SUBDIRS:
            (project_root / sub).mkdir()
        meta = ProjectMeta(slug=slug, name=name, description=description)
        project = Project(meta=meta, root=project_root)
        project.save()
        logger.info("Nieuw project aangemaakt: {} ({})", name, slug)
        return project

    def open(self, slug: str) -> Project:
        project_root = self.root / slug
        if not (project_root / PROJECT_FILE).is_file():
            raise FileNotFoundError(f"Project niet gevonden: {slug}")
        return Project.load(project_root)

    def delete(self, slug: str) -> None:
        """Verwijder volledig project-mapje (inclusief scans!)."""
        project_root = self.root / slug
        if project_root.is_dir():
            shutil.rmtree(project_root)
            logger.warning("Project verwijderd: {}", slug)
