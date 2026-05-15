"""Centrale configuratie. Laadt config.json indien aanwezig, anders defaults."""

from __future__ import annotations

import json
import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


# --- Default zoeklocaties voor externe binaries op Windows -----------------

_TESSERACT_HINTS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
]

_GHOSTSCRIPT_HINTS = [
    r"C:\Program Files\gs\gs10.04.0\bin\gswin64c.exe",
    r"C:\Program Files\gs\gs10.03.0\bin\gswin64c.exe",
    r"C:\Program Files\gs\gs10.02.1\bin\gswin64c.exe",
]


def _find_executable(explicit: str, env_name: str, hints: List[str]) -> Optional[str]:
    """Zoek een executable: expliciet pad → env-var → PATH → hint-lijst."""
    if explicit and Path(explicit).is_file():
        return explicit
    env = os.environ.get(env_name)
    if env and Path(env).is_file():
        return env
    on_path = shutil.which(Path(hints[0]).stem if hints else env_name.lower())
    if on_path:
        return on_path
    for hint in hints:
        # Glob support voor versie-suffixen (bv. gs10.*)
        if "*" in hint:
            matches = sorted(Path(hint).parent.glob(Path(hint).name), reverse=True)
            if matches:
                return str(matches[0])
        elif Path(hint).is_file():
            return hint
    return None


# --- Pydantic-modellen voor structuur --------------------------------------


class TesseractCfg(BaseModel):
    executable: str = ""
    languages: List[str] = Field(default_factory=lambda: ["nld", "eng", "deu", "fra"])
    default_psm: int = 3


class GhostscriptCfg(BaseModel):
    executable: str = ""


class ImageProcessingCfg(BaseModel):
    auto_deskew: bool = True
    auto_crop: bool = True
    auto_enhance_old_paper: bool = True
    two_page_split_default: bool = False


class SpellcheckCfg(BaseModel):
    enabled: bool = True
    language: str = "nl-NL"


class ServerCfg(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765


class UiCfg(BaseModel):
    large_buttons: bool = True
    show_advanced: bool = False


class UpdatesCfg(BaseModel):
    enabled: bool = True
    github_owner: str = "vectrus"
    github_repo: str = "ScannerApp"
    asset_name: str = "BoekScanner-windows.zip"


class Config(BaseModel):
    """Volledige app-configuratie."""

    data_dir: Path = Field(default=Path("./data"))
    inbox_dir: Path = Field(default=Path("./data/inbox"))
    projects_dir: Path = Field(default=Path("./data/projects"))
    tessdata_dir: Path = Field(default=Path("./data/tessdata"))
    tesseract: TesseractCfg = Field(default_factory=TesseractCfg)
    ghostscript: GhostscriptCfg = Field(default_factory=GhostscriptCfg)
    image_processing: ImageProcessingCfg = Field(default_factory=ImageProcessingCfg)
    spellcheck: SpellcheckCfg = Field(default_factory=SpellcheckCfg)
    server: ServerCfg = Field(default_factory=ServerCfg)
    ui: UiCfg = Field(default_factory=UiCfg)
    updates: UpdatesCfg = Field(default_factory=UpdatesCfg)

    # --- helpers -----------------------------------------------------------

    def resolve_tesseract(self) -> Optional[str]:
        return _find_executable(self.tesseract.executable, "TESSERACT_PATH", _TESSERACT_HINTS)

    def resolve_ghostscript(self) -> Optional[str]:
        return _find_executable(self.ghostscript.executable, "GHOSTSCRIPT_PATH", _GHOSTSCRIPT_HINTS)

    def resolve_tessdata_dir(self) -> Optional[Path]:
        """Geef de gebruikers-tessdata-map terug als die taalbestanden bevat.

        Hiermee kan BoekScanner taalbestanden bundelen zonder admin-rechten
        nodig te hebben voor schrijven naar Program Files.
        """
        d = Path(self.tessdata_dir)
        if d.is_dir() and any(d.glob("*.traineddata")):
            return d
        return None

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.inbox_dir, self.projects_dir, self.tessdata_dir):
            Path(path).mkdir(parents=True, exist_ok=True)


# --- Loader ----------------------------------------------------------------


def _app_root() -> Path:
    """Root van de app — werkt zowel in dev als wanneer gebundeld via PyInstaller."""
    if getattr(sys, "frozen", False):
        # In PyInstaller-bundle wijst sys.executable naar de .exe
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def _strip_comments(raw: dict) -> dict:
    """Verwijdert ALLE keys die met '_' beginnen (commentaar-velden in JSON)."""
    if isinstance(raw, dict):
        return {k: _strip_comments(v) for k, v in raw.items() if not k.startswith("_")}
    if isinstance(raw, list):
        return [_strip_comments(v) for v in raw]
    return raw


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Laad config.json als die bestaat; anders defaults. Resolve relatieve paden."""
    root = _app_root()
    cfg_path = root / "config.json"
    raw: dict = {}
    if cfg_path.is_file():
        with cfg_path.open("r", encoding="utf-8") as f:
            raw = _strip_comments(json.load(f))
    cfg = Config(**raw)

    # Maak relatieve paden absoluut t.o.v. de app-root
    if not cfg.data_dir.is_absolute():
        cfg.data_dir = (root / cfg.data_dir).resolve()
    if not cfg.inbox_dir.is_absolute():
        cfg.inbox_dir = (root / cfg.inbox_dir).resolve()
    if not cfg.projects_dir.is_absolute():
        cfg.projects_dir = (root / cfg.projects_dir).resolve()
    if not cfg.tessdata_dir.is_absolute():
        cfg.tessdata_dir = (root / cfg.tessdata_dir).resolve()

    cfg.ensure_dirs()
    return cfg


def reload_config() -> Config:
    """Forceer herladen (voor tests of na config-wijziging via UI)."""
    get_config.cache_clear()
    return get_config()
