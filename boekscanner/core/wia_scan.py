"""Direct scannen via Windows WIA (Windows Image Acquisition).

Werkt met de meeste Canon-modellen die WIA-drivers leveren. We gebruiken
PowerShell + de WIA COM-componenten — geen extra Python-dependencies nodig.

Beperkingen:
- Werkt alleen op Windows.
- Sommige Canon-modellen vereisen TWAIN i.p.v. WIA. In dat geval moet de
  gebruiker NAPS2 / Canon-software gebruiken (de inbox-watcher pakt het op).

Gebruik:

::

    from boekscanner.core.wia_scan import scan_to_inbox, list_scanners
    scanners = list_scanners()
    out_path = scan_to_inbox(dpi=300, color="color")
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

from loguru import logger

from .config import get_config


ColorMode = Literal["color", "grayscale", "blackwhite"]


# WIA-constanten
_WIA_COLOR = {"color": 1, "grayscale": 2, "blackwhite": 4}

# WIA Property IDs
_PROP_HORIZONTAL_RES = 6147
_PROP_VERTICAL_RES = 6148
_PROP_CURRENT_INTENT = 6146
_FORMAT_PNG = "{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}"
_FORMAT_JPEG = "{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}"


@dataclass
class ScannerInfo:
    device_id: str
    name: str
    manufacturer: str
    description: str = ""


class WiaError(RuntimeError):
    """Specifieke fout vanuit WIA-laag (apparaat niet gevonden, drivers ontbreken, ...)."""


def _ensure_windows() -> None:
    if platform.system() != "Windows":
        raise WiaError("WIA scannen is alleen beschikbaar op Windows.")


def _run_powershell(script: str, timeout: int = 120) -> str:
    """Voer een PowerShell-blok uit en geef stdout terug. Raise bij fout."""
    _ensure_windows()
    cmd = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-Command", script,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise WiaError(
            f"PowerShell mislukt (code {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


# --- Lijst beschikbare scanners --------------------------------------------


_PS_LIST_SCANNERS = r"""
$ErrorActionPreference = 'Stop'
try {
    $manager = New-Object -ComObject WIA.DeviceManager
} catch {
    Write-Error "WIA niet beschikbaar: $_"
    exit 1
}
$devices = @()
foreach ($info in $manager.DeviceInfos) {
    if ($info.Type -ne 1) { continue } # 1 = Scanner
    $name = ""
    $manuf = ""
    $desc = ""
    foreach ($p in $info.Properties) {
        switch ($p.PropertyID) {
            7  { $name  = $p.Value }
            3  { $manuf = $p.Value }
            4  { $desc  = $p.Value }
        }
    }
    $devices += [ordered]@{
        device_id    = $info.DeviceID
        name         = $name
        manufacturer = $manuf
        description  = $desc
    }
}
$devices | ConvertTo-Json -Compress
"""


def list_scanners() -> List[ScannerInfo]:
    """Geef een lijst van beschikbare WIA-scanners."""
    _ensure_windows()
    try:
        out = _run_powershell(_PS_LIST_SCANNERS).strip()
    except WiaError as exc:
        logger.warning("Kan WIA-scanners niet ophalen: {}", exc)
        return []
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError as exc:
        logger.warning("Onverwachte WIA-output: {}", out)
        raise WiaError(f"Kan scanner-lijst niet parsen: {exc}") from exc
    if isinstance(data, dict):
        data = [data]
    return [
        ScannerInfo(
            device_id=item.get("device_id", ""),
            name=item.get("name", ""),
            manufacturer=item.get("manufacturer", ""),
            description=item.get("description", ""),
        )
        for item in data
    ]


# --- Scan-actie ------------------------------------------------------------


_PS_SCAN_TEMPLATE = r"""
$ErrorActionPreference = 'Stop'
try {
    $manager = New-Object -ComObject WIA.DeviceManager
} catch {
    Write-Error "WIA niet beschikbaar: $_"
    exit 1
}

$deviceIdFilter = '__DEVICE_ID__'
$dpi            = __DPI__
$intent         = __INTENT__
$outputPath     = '__OUTPUT_PATH__'
$formatId       = '__FORMAT__'

$device = $null
foreach ($info in $manager.DeviceInfos) {
    if ($info.Type -ne 1) { continue }
    if ([string]::IsNullOrEmpty($deviceIdFilter) -or $info.DeviceID -eq $deviceIdFilter) {
        $device = $info.Connect()
        break
    }
}
if ($null -eq $device) {
    Write-Error "Geen geschikte WIA-scanner gevonden."
    exit 2
}

$item = $device.Items.Item(1)

# Helper om een eigenschap veilig te zetten
function Set-WiaProp($props, $id, $value) {
    foreach ($p in $props) {
        if ($p.PropertyID -eq $id) {
            try { $p.Value = $value } catch { }
            return
        }
    }
}

Set-WiaProp $item.Properties 6147 $dpi  # X DPI
Set-WiaProp $item.Properties 6148 $dpi  # Y DPI
Set-WiaProp $item.Properties 6146 $intent  # Current Intent (color/grayscale/bw)

$image = $item.Transfer($formatId)
if (Test-Path $outputPath) { Remove-Item -LiteralPath $outputPath -Force }
$image.SaveFile($outputPath)
Write-Output $outputPath
"""


def scan_to_inbox(
    *,
    device_id: Optional[str] = None,
    dpi: int = 300,
    color: ColorMode = "color",
    output_format: Literal["png", "jpeg"] = "png",
    timeout: int = 180,
) -> Path:
    """Scan één pagina en sla op in de inbox-map. Geeft het pad terug."""
    _ensure_windows()
    cfg = get_config()
    cfg.inbox_dir.mkdir(parents=True, exist_ok=True)

    intent = _WIA_COLOR.get(color, _WIA_COLOR["color"])
    fmt_id = _FORMAT_PNG if output_format == "png" else _FORMAT_JPEG
    ext = "png" if output_format == "png" else "jpg"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    out_name = f"scan-{timestamp}-{uuid.uuid4().hex[:6]}.{ext}"
    out_path = (cfg.inbox_dir / out_name).resolve()

    script = (
        _PS_SCAN_TEMPLATE
        .replace("__DEVICE_ID__", device_id or "")
        .replace("__DPI__", str(int(dpi)))
        .replace("__INTENT__", str(intent))
        .replace("__OUTPUT_PATH__", str(out_path).replace("'", "''"))
        .replace("__FORMAT__", fmt_id)
    )

    logger.info(
        "Start WIA-scan naar {} (dpi={}, kleur={}, formaat={})",
        out_path.name, dpi, color, output_format,
    )
    _run_powershell(script, timeout=timeout)

    if not out_path.is_file():
        raise WiaError(f"Scan voltooid maar bestand ontbreekt: {out_path}")
    return out_path
