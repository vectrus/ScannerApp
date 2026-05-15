"""Image-processing voor boek-scans.

Bevat:
- ``deskew`` — rechtzetten van scheve scans
- ``auto_crop`` — witruimte/zwarte rand wegsnijden
- ``enhance_old_paper`` — contrast- en helderheidcorrectie voor vergeeld papier
- ``split_two_pages`` — opengeslagen boek (linker + rechter pagina) splitsen
- ``process_page`` — alles-in-een pipeline op basis van settings

Alle functies werken met ``numpy.ndarray`` (BGR, OpenCV-conventie).
Helpers ``load_image``/``save_image`` voor bestand-I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from loguru import logger


# --- I/O helpers -----------------------------------------------------------


def load_image(path: Path) -> np.ndarray:
    """Laad een afbeelding (BGR). Werkt ook met paden met niet-ASCII tekens."""
    raw = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Kan afbeelding niet laden: {path}")
    return img


def save_image(img: np.ndarray, path: Path, quality: int = 92) -> None:
    """Sla afbeelding op (PNG/JPEG op basis van extensie). Unicode-pad-veilig."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower() or ".png"
    if ext in {".jpg", ".jpeg"}:
        ok, buf = cv2.imencode(ext, img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    elif ext == ".png":
        ok, buf = cv2.imencode(ext, img, [int(cv2.IMWRITE_PNG_COMPRESSION), 4])
    else:
        ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise IOError(f"Kan afbeelding niet schrijven: {path}")
    buf.tofile(str(path))


# --- Deskew (rechtzetten) --------------------------------------------------


def _grayscale(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def estimate_skew_angle(img: np.ndarray, max_abs_deg: float = 15.0) -> float:
    """Schat de hoek (in graden) waaronder tekst ligt t.o.v. horizontaal.

    Gebruikt minimum-area-bounding-box rond donkere pixels (klassiek aanpak).
    Beperkt tot ±``max_abs_deg`` om wilde uitschieters te voorkomen.
    """
    gray = _grayscale(img)
    # Tekst → wit; achtergrond → zwart
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(bw > 0))
    if coords.size < 50:
        return 0.0
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    # OpenCV normaliseert hoek tussen 0 en 90; we willen ±45
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) > max_abs_deg:
        logger.debug("Skew-hoek {:.2f}° overschrijdt limiet, negeer.", angle)
        return 0.0
    return float(angle)


def deskew(img: np.ndarray) -> np.ndarray:
    """Rechtzetten van een scan op basis van geschatte tekst-hoek."""
    angle = estimate_skew_angle(img)
    if abs(angle) < 0.1:
        return img
    h, w = img.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(
        img, matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


# --- Auto-crop -------------------------------------------------------------


def auto_crop(img: np.ndarray, margin_pct: float = 0.01) -> np.ndarray:
    """Snij witruimte/zwart rondom de pagina weg.

    ``margin_pct`` voegt een kleine marge toe zodat we geen tekst raken.
    """
    gray = _grayscale(img)
    # Zachte blur om scan-ruis weg te halen
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Otsu — scheidt papier van scanner-rand
    _, bw = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Pak het grootste contour (de pagina)
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img
    biggest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(biggest)
    # Sanity check: bounding-box moet realistisch groot zijn
    if w * h < 0.2 * gray.shape[0] * gray.shape[1]:
        logger.debug("Auto-crop: pagina-detectie onbetrouwbaar, geen crop.")
        return img
    mx = int(w * margin_pct)
    my = int(h * margin_pct)
    x0 = max(0, x - mx)
    y0 = max(0, y - my)
    x1 = min(img.shape[1], x + w + mx)
    y1 = min(img.shape[0], y + h + my)
    return img[y0:y1, x0:x1]


# --- Beeldverbetering vergeeld papier --------------------------------------


def enhance_old_paper(img: np.ndarray) -> np.ndarray:
    """Maak vergeeld/laag-contrast oud papier weer goed leesbaar.

    Strategie:
      1. CLAHE op de L-kanaal (LAB) → versterkt lokaal contrast.
      2. Witpunt-verschuiving in HSV → maakt ivoor papier weer wit-achtig.
      3. Lichte ``unsharp mask`` → tekst-randen scherper.

    De originele kleuren blijven globaal herkenbaar — bedoeld voor leesbare
    OCR + nette uitstraling in PDF/Word, niet om scans 'pure zwart-wit' te maken.
    """
    # 1) CLAHE op L-kanaal
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    lab_eq = cv2.merge((l_eq, a, b))
    enhanced = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)

    # 2) Witpunt-verschuiving — bovenste 1% lichtste pixels → wit
    flat = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY).flatten()
    if flat.size:
        white_point = np.percentile(flat, 99)
        if white_point > 0:
            scale = 255.0 / white_point
            enhanced = np.clip(enhanced.astype(np.float32) * scale, 0, 255).astype(np.uint8)

    # 3) Unsharp mask
    blur = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.5)
    sharpened = cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)
    return sharpened


# --- Two-page splitter -----------------------------------------------------


def split_two_pages(img: np.ndarray, gutter_search_pct: float = 0.2) -> List[np.ndarray]:
    """Splits een scan van een opengeslagen boek in linker- en rechterpagina.

    Zoekt de 'gutter' (donkere bandkloof in het midden) door de gemiddelde
    helderheid per kolom te analyseren in een venster rond het midden van
    breedte ``gutter_search_pct``. Geeft een lijst van 1 of 2 afbeeldingen.
    """
    h, w = img.shape[:2]
    gray = _grayscale(img)
    # Pak alleen de middelste 60% in hoogte (vermijd kop/voet ruis)
    y0 = int(h * 0.2)
    y1 = int(h * 0.8)
    column_mean = gray[y0:y1, :].mean(axis=0)

    mid = w // 2
    half_window = int(w * gutter_search_pct / 2)
    lo = max(0, mid - half_window)
    hi = min(w, mid + half_window)

    if hi - lo < 5:
        return [img]

    # Donkerste kolom = waarschijnlijkste gutter
    rel_min_idx = int(np.argmin(column_mean[lo:hi]))
    gutter = lo + rel_min_idx

    # Sanity: gutter moet duidelijk donkerder zijn dan papier-gemiddelde
    paper_avg = column_mean.mean()
    gutter_val = column_mean[gutter]
    if gutter_val > paper_avg * 0.85:
        logger.debug("Geen duidelijke gutter gevonden — geen split.")
        return [img]

    left = img[:, :gutter]
    right = img[:, gutter:]
    # Filter te smalle stukken
    if left.shape[1] < w * 0.2 or right.shape[1] < w * 0.2:
        return [img]
    return [left, right]


# --- Pipeline --------------------------------------------------------------


@dataclass
class ProcessingOptions:
    deskew: bool = True
    crop: bool = True
    enhance: bool = True
    split_pages: bool = False


def process_page(img: np.ndarray, options: ProcessingOptions) -> List[np.ndarray]:
    """Volledige pipeline. Geeft 1 (of 2 bij split) verwerkte afbeelding(en)."""
    if options.split_pages:
        pieces = split_two_pages(img)
    else:
        pieces = [img]

    out: List[np.ndarray] = []
    for piece in pieces:
        if options.deskew:
            piece = deskew(piece)
        if options.crop:
            piece = auto_crop(piece)
        if options.enhance:
            piece = enhance_old_paper(piece)
        out.append(piece)
    return out


# --- Thumbnail -------------------------------------------------------------


def make_thumbnail(img: np.ndarray, max_side: int = 240) -> np.ndarray:
    """Maakt een thumbnail met behoud van aspect-ratio."""
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale >= 1:
        return img.copy()
    new_size = (int(w * scale), int(h * scale))
    return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
