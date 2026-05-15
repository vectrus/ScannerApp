"""GitHub Release based updater for BoekScanner.

The app checks the latest public GitHub release, downloads the configured ZIP
asset, then starts a small PowerShell helper that replaces app files after the
current process exits. User data in ``data/`` is deliberately left untouched.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from .. import __version__
from ..build_info import BUILD_COMMIT, BUILD_ID, BUILD_TIME
from .config import get_config


GITHUB_API = "https://api.github.com"


@dataclass
class UpdateAsset:
    name: str
    download_url: str
    size_bytes: int


@dataclass
class UpdateCheck:
    enabled: bool
    configured: bool
    current_version: str
    current_build_id: str
    current_build_time: str
    remote_version: Optional[str] = None
    remote_build_id: Optional[str] = None
    release_name: Optional[str] = None
    release_notes_url: Optional[str] = None
    published_at: Optional[str] = None
    available: bool = False
    asset: Optional[UpdateAsset] = None
    message: str = ""


def app_root() -> Path:
    """Return the folder that should be replaced by an update."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _json_get(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "BoekScanner-updater",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _find_asset(release: dict[str, Any], wanted_name: str) -> Optional[UpdateAsset]:
    assets = release.get("assets") or []
    for asset in assets:
        if asset.get("name") == wanted_name:
            return UpdateAsset(
                name=asset["name"],
                download_url=asset["browser_download_url"],
                size_bytes=int(asset.get("size") or 0),
            )
    for asset in assets:
        name = str(asset.get("name") or "")
        if name.lower().endswith(".zip") and "boekscanner" in name.lower():
            return UpdateAsset(
                name=name,
                download_url=asset["browser_download_url"],
                size_bytes=int(asset.get("size") or 0),
            )
    return None


def _release_from_public_web(owner: str, repo: str, asset_name: str) -> dict[str, Any]:
    """Resolve latest public release without the GitHub API.

    The GitHub API is convenient but rate-limited for anonymous users. Because
    this app updates from a public repo with a predictable asset name, we can
    follow the public /releases/latest redirect and use /latest/download/<asset>.
    """
    latest_url = f"https://github.com/{owner}/{repo}/releases/latest"
    req = urllib.request.Request(latest_url, headers={"User-Agent": "BoekScanner-updater"})
    with urllib.request.urlopen(req, timeout=20) as response:
        final_url = response.geturl()

    marker = "/releases/tag/"
    if marker not in final_url:
        raise RuntimeError("Kon laatste GitHub Release niet bepalen.")
    tag = final_url.rsplit(marker, 1)[1].split("?", 1)[0].split("#", 1)[0]
    asset_url = f"https://github.com/{owner}/{repo}/releases/latest/download/{asset_name}"
    return {
        "tag_name": tag,
        "name": f"BoekScanner {tag}",
        "html_url": final_url,
        "published_at": None,
        "assets": [
            {
                "name": asset_name,
                "browser_download_url": asset_url,
                "size": 0,
            }
        ],
    }


def check_for_update() -> UpdateCheck:
    cfg = get_config()
    updates = cfg.updates
    configured = bool(updates.github_owner and updates.github_repo)
    result = UpdateCheck(
        enabled=updates.enabled,
        configured=configured,
        current_version=__version__,
        current_build_id=BUILD_ID,
        current_build_time=BUILD_TIME,
    )

    if not updates.enabled:
        result.message = "Updates zijn uitgeschakeld."
        return result
    if not configured:
        result.message = "GitHub-repository is nog niet ingesteld in config.json."
        return result

    url = f"{GITHUB_API}/repos/{updates.github_owner}/{updates.github_repo}/releases/latest"
    try:
        release = _json_get(url)
    except Exception as exc:
        logger.info("GitHub API update-check mislukt ({}), probeer publieke release-url.", exc)
        try:
            release = _release_from_public_web(
                updates.github_owner,
                updates.github_repo,
                updates.asset_name,
            )
        except urllib.error.HTTPError as web_exc:
            if web_exc.code == 404:
                result.message = "Nog geen GitHub Release gevonden."
            else:
                result.message = f"GitHub gaf fout {web_exc.code} terug."
            return result
        except Exception as web_exc:
            result.message = f"Kan GitHub niet bereiken: {web_exc}"
            return result

    asset = _find_asset(release, updates.asset_name)
    tag = str(release.get("tag_name") or "")
    result.remote_version = tag.lstrip("v")
    result.remote_build_id = tag
    result.release_name = release.get("name") or tag
    result.release_notes_url = release.get("html_url")
    result.published_at = release.get("published_at")
    result.asset = asset

    if asset is None:
        result.message = f"Release gevonden, maar asset {updates.asset_name!r} ontbreekt."
        return result

    # GitHub Actions uses the release tag as build id. Dev builds always see a
    # release as available, which is convenient while testing.
    result.available = BUILD_ID == "dev" or (tag and tag != BUILD_ID)
    result.message = "Update beschikbaar." if result.available else "BoekScanner is up-to-date."
    return result


def _download_file(url: str, target: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "BoekScanner-updater"})
    with urllib.request.urlopen(req, timeout=120) as response, target.open("wb") as f:
        shutil.copyfileobj(response, f)


def download_update() -> Path:
    check = check_for_update()
    if not check.available or check.asset is None:
        raise RuntimeError(check.message or "Geen update beschikbaar.")

    cfg = get_config()
    updates_dir = cfg.data_dir / "updates" / (check.remote_build_id or "latest")
    updates_dir.mkdir(parents=True, exist_ok=True)
    zip_path = updates_dir / check.asset.name
    logger.info("Download update {} naar {}", check.asset.download_url, zip_path)
    _download_file(check.asset.download_url, zip_path)
    return zip_path


def _find_payload_root(extract_dir: Path) -> Path:
    """Return extracted root; accepts ZIPs with or without a BoekScanner folder."""
    direct_exe = extract_dir / "BoekScanner.exe"
    if direct_exe.is_file():
        return extract_dir
    nested = extract_dir / "BoekScanner" / "BoekScanner.exe"
    if nested.is_file():
        return extract_dir / "BoekScanner"
    matches = list(extract_dir.glob("*/BoekScanner.exe"))
    if matches:
        return matches[0].parent
    raise RuntimeError("Update-zip bevat geen BoekScanner.exe.")


def prepare_update(zip_path: Path) -> Path:
    cfg = get_config()
    work_dir = cfg.data_dir / "updates" / "prepared"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    extract_dir = work_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    payload_root = _find_payload_root(extract_dir)
    script_path = work_dir / "apply_update.ps1"
    target_root = app_root()
    current_pid = os.getpid()
    is_packaged = bool(getattr(sys, "frozen", False))
    restart_exe = str(sys.executable if is_packaged else Path(sys.executable).resolve())
    restart_args = "" if is_packaged else " ".join(repr(arg) for arg in sys.argv)

    script = f"""$ErrorActionPreference = 'Stop'
$source = {str(payload_root)!r}
$target = {str(target_root)!r}
$pidToWait = {current_pid}
$restartExe = {restart_exe!r}
$restartArgs = {restart_args!r}
$isPackaged = ${str(is_packaged).lower()}

Write-Host 'BoekScanner wordt bijgewerkt...'
try {{
  Wait-Process -Id $pidToWait -Timeout 60 -ErrorAction SilentlyContinue
}} catch {{}}
Start-Sleep -Seconds 2

Get-ChildItem -Path $source -Force | ForEach-Object {{
  $dest = Join-Path $target $_.Name
  if ($_.Name -in @('data', 'config.json')) {{
    return
  }}
  if (Test-Path $dest) {{
    Remove-Item -Path $dest -Recurse -Force
  }}
  Copy-Item -Path $_.FullName -Destination $dest -Recurse -Force
}}

$exe = Join-Path $target 'BoekScanner.exe'
if (Test-Path $exe) {{
  Start-Process -FilePath $exe
}} elseif (-not $isPackaged -and (Test-Path $restartExe)) {{
  Start-Process -FilePath $restartExe -ArgumentList $restartArgs -WorkingDirectory $target
}}
"""
    script_path.write_text(script, encoding="utf-8")
    return script_path


def launch_update_script(script_path: Path) -> None:
    if not script_path.is_file():
        raise RuntimeError(f"Update-script niet gevonden: {script_path}")
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        cwd=str(app_root()),
        creationflags=0x08000000 if os.name == "nt" else 0,
    )
