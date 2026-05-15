"""Tesseract-wrapper voor OCR.

Functies:
- ``check_tesseract`` — verifieer dat Tesseract bereikbaar is + welke talen.
- ``ocr_image`` — OCR op één afbeelding (numpy of pad), met taal-keuze.
- ``ocr_to_hocr`` — OCR die hOCR teruggeeft (gebruikt door ocrmypdf).
- ``OcrResult`` — dataclass met tekst, gemiddelde confidence en woord-info.

Tesseract zelf wordt extern geïnstalleerd (zie ``installer/``); dit module
detecteert het pad via ``Config.resolve_tesseract`` en zet
``pytesseract.pytesseract.tesseract_cmd`` éénmalig.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Union

import numpy as np
import pytesseract
from loguru import logger
from PIL import Image

from .config import get_config

ImageInput = Union[np.ndarray, Path, str, Image.Image]


# --- Initialisatie ---------------------------------------------------------


_initialized = False
_tessdata_config_flag: str = ""


def _quote_path(path: str) -> str:
    """Wrap path in double quotes if it contains spaces."""
    if " " in path and not (path.startswith('"') and path.endswith('"')):
        return f'"{path}"'
    return path


def _ensure_initialized() -> None:
    global _initialized, _tessdata_config_flag
    if _initialized:
        return
    cfg = get_config()
    exe = cfg.resolve_tesseract()
    if exe:
        pytesseract.pytesseract.tesseract_cmd = exe
        logger.info("Tesseract gevonden: {}", exe)
    else:
        logger.warning(
            "Tesseract NIET gevonden. Installeer via installer/install_dependencies.ps1 "
            "of zet het pad in config.json onder tesseract.executable."
        )

    # Eigen tessdata-map aanwijzen indien gevuld (geen admin nodig).
    tessdata = cfg.resolve_tessdata_dir()
    if tessdata is not None:
        _tessdata_config_flag = f"--tessdata-dir {_quote_path(str(tessdata))}"
        logger.info("Tessdata-map (gebruikersmap): {}", tessdata)
    _initialized = True


def _build_config(psm_val: int) -> str:
    """Bouw de --psm en eventueel --tessdata-dir flags."""
    parts = [f"--psm {psm_val}"]
    if _tessdata_config_flag:
        parts.insert(0, _tessdata_config_flag)
    return " ".join(parts)


# --- Diagnose -------------------------------------------------------------


@dataclass
class TesseractStatus:
    available: bool
    version: Optional[str] = None
    executable: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    error: Optional[str] = None


def _list_languages(exe: str) -> List[str]:
    """List taalpakketten via een directe `tesseract --list-langs` call.

    pytesseract.get_languages() ondersteunt --tessdata-dir niet betrouwbaar,
    dus we runnen tesseract zelf en parsen de output.
    """
    import subprocess

    cfg = get_config()
    args = [exe, "--list-langs"]
    tessdata = cfg.resolve_tessdata_dir()
    if tessdata is not None:
        args += ["--tessdata-dir", str(tessdata)]
    try:
        # CREATE_NO_WINDOW=0x08000000 voorkomt console-flits op Windows
        creationflags = 0x08000000 if os.name == "nt" else 0
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=creationflags,
        )
        out = (result.stdout + "\n" + result.stderr).splitlines()
        langs: List[str] = []
        for line in out:
            line = line.strip()
            # Skip header line + lege regels
            if not line or line.lower().startswith("list of available"):
                continue
            # Een taal is altijd een korte alfanumerieke string zonder spaties
            if " " not in line and 2 <= len(line) <= 12:
                langs.append(line)
        return langs
    except Exception as exc:
        logger.warning("Kon taalpakketten niet lijsten: {}", exc)
        return []


def check_tesseract() -> TesseractStatus:
    """Geef de huidige Tesseract-status terug (voor de UI/installer-check)."""
    _ensure_initialized()
    exe = pytesseract.pytesseract.tesseract_cmd
    try:
        version = str(pytesseract.get_tesseract_version())
        languages = _list_languages(exe)
        return TesseractStatus(
            available=True,
            version=version,
            executable=exe,
            languages=languages,
        )
    except Exception as exc:
        return TesseractStatus(available=False, executable=exe, error=str(exc))


# --- OCR ------------------------------------------------------------------


@dataclass
class OcrWord:
    text: str
    confidence: float
    bbox: tuple  # (x, y, w, h) in pixels


@dataclass
class OcrResult:
    text: str
    languages: str  # bv. "nld+eng"
    avg_confidence: float
    words: List[OcrWord] = field(default_factory=list)
    psm: int = 3

    @property
    def word_count(self) -> int:
        return len(self.words)


def _to_pil(image: ImageInput) -> Image.Image:
    if isinstance(image, Image.Image):
        return image
    if isinstance(image, (str, Path)):
        return Image.open(str(image))
    if isinstance(image, np.ndarray):
        # OpenCV BGR → PIL RGB
        if image.ndim == 3 and image.shape[2] == 3:
            return Image.fromarray(image[:, :, ::-1])
        return Image.fromarray(image)
    raise TypeError(f"Onbekend afbeeldingstype: {type(image)}")


def _resolve_languages(requested: Optional[Sequence[str]]) -> str:
    cfg = get_config()
    langs = list(requested) if requested else list(cfg.tesseract.languages)
    return "+".join(langs) if langs else "eng"


def ocr_image(
    image: ImageInput,
    languages: Optional[Sequence[str]] = None,
    psm: Optional[int] = None,
) -> OcrResult:
    """OCR een enkele afbeelding. Geeft tekst + woord-confidence terug."""
    _ensure_initialized()
    cfg = get_config()
    pil = _to_pil(image)
    lang_str = _resolve_languages(languages)
    psm_val = psm if psm is not None else cfg.tesseract.default_psm
    config_str = _build_config(psm_val)

    try:
        data = pytesseract.image_to_data(
            pil,
            lang=lang_str,
            config=config_str,
            output_type=pytesseract.Output.DICT,
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract is niet geïnstalleerd of niet vindbaar. "
            "Voer installer/install_dependencies.ps1 uit."
        ) from exc

    words: List[OcrWord] = []
    confidences: List[float] = []
    text_lines: dict[tuple, list[str]] = {}

    n = len(data["text"])
    for i in range(n):
        raw_text = (data["text"][i] or "").strip()
        if not raw_text:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 0:
            continue
        x, y, w, h = (
            int(data["left"][i]),
            int(data["top"][i]),
            int(data["width"][i]),
            int(data["height"][i]),
        )
        words.append(OcrWord(text=raw_text, confidence=conf, bbox=(x, y, w, h)))
        confidences.append(conf)
        key = (
            int(data["block_num"][i]),
            int(data["par_num"][i]),
            int(data["line_num"][i]),
        )
        text_lines.setdefault(key, []).append(raw_text)

    # Reconstrueer tekst in lees-volgorde (block → paragraph → line)
    sorted_keys = sorted(text_lines.keys())
    lines: List[str] = []
    last_block_par: Optional[tuple] = None
    for key in sorted_keys:
        block_par = key[:2]
        if last_block_par is not None and block_par != last_block_par:
            lines.append("")  # lege regel tussen paragrafen/blokken
        lines.append(" ".join(text_lines[key]))
        last_block_par = block_par
    text = "\n".join(lines).strip()

    avg_conf = float(np.mean(confidences)) if confidences else 0.0
    return OcrResult(
        text=text,
        languages=lang_str,
        avg_confidence=avg_conf,
        words=words,
        psm=psm_val,
    )


def ocr_to_hocr(
    image: ImageInput,
    languages: Optional[Sequence[str]] = None,
    psm: Optional[int] = None,
) -> bytes:
    """Geeft hOCR (HTML met posities) terug — handig om tekstlaag in PDF te bouwen.

    Wordt momenteel gebruikt door batch-pipeline; ``ocrmypdf`` doet hOCR intern
    en is meestal de betere route voor doorzoekbare PDF.
    """
    _ensure_initialized()
    cfg = get_config()
    pil = _to_pil(image)
    lang_str = _resolve_languages(languages)
    psm_val = psm if psm is not None else cfg.tesseract.default_psm
    config_str = _build_config(psm_val)
    return pytesseract.image_to_pdf_or_hocr(
        pil, lang=lang_str, config=config_str, extension="hocr"
    )
