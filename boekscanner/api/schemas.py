"""Pydantic-schemas voor request/response validation."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# --- Projecten -------------------------------------------------------------


class CreateProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class ProjectListItem(BaseModel):
    slug: str
    name: str
    pages: int
    created_at: str
    updated_at: str
    description: str = ""


class PageOut(BaseModel):
    id: str
    index: int  # 1-based positie in het project
    width: Optional[int]
    height: Optional[int]
    has_processed: bool
    has_thumb: bool
    has_ocr: bool
    text_preview: Optional[str]
    avg_confidence: Optional[float]
    rotation_degrees: int = 0
    created_at: str


class ProjectDetailOut(BaseModel):
    slug: str
    name: str
    description: str
    created_at: str
    updated_at: str
    settings: dict
    pages: List[PageOut]


# --- Pagina-acties ---------------------------------------------------------


class ReorderPagesIn(BaseModel):
    page_ids: List[str]


class UpdateOcrIn(BaseModel):
    text: str


class ReprocessIn(BaseModel):
    deskew: Optional[bool] = None
    crop: Optional[bool] = None
    enhance: Optional[bool] = None
    split_pages: Optional[bool] = None
    force_split: bool = False
    rotation_degrees: Optional[int] = None
    rerun_ocr: bool = True


# --- Settings --------------------------------------------------------------


class ProjectSettingsIn(BaseModel):
    languages: Optional[List[str]] = None
    psm: Optional[int] = None
    auto_deskew: Optional[bool] = None
    auto_crop: Optional[bool] = None
    auto_enhance_old_paper: Optional[bool] = None
    two_page_split: Optional[bool] = None
    spellcheck_enabled: Optional[bool] = None


# --- Scannen ---------------------------------------------------------------


class ScannerOut(BaseModel):
    device_id: str
    name: str
    manufacturer: str
    description: str = ""


class ScanRequestIn(BaseModel):
    device_id: Optional[str] = None
    dpi: int = 300
    color: str = "color"  # 'color' | 'grayscale' | 'blackwhite'
    output_format: str = "png"  # 'png' | 'jpeg'


# --- Export ---------------------------------------------------------------


class ExportIn(BaseModel):
    formats: List[str]  # 'pdf' | 'docx' | 'txt' | 'md'
    per_page: bool = True
    combined: bool = True


class ExportFileOut(BaseModel):
    label: str
    download_url: str
    size_bytes: int


class ExportResponseOut(BaseModel):
    files: List[ExportFileOut]


# --- Spellcheck ------------------------------------------------------------


class SpellSuggestionOut(BaseModel):
    offset: int
    length: int
    message: str
    rule_id: str
    suggestions: List[str]


# --- Status ----------------------------------------------------------------


class StatusOut(BaseModel):
    app_version: str
    tesseract_available: bool
    tesseract_version: Optional[str]
    tesseract_languages: List[str]
    inbox_dir: str
    pending_inbox_files: int
    active_project: Optional[str]
