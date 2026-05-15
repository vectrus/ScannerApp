"""Inbox-watcher: monitort ``data/inbox`` voor nieuwe scans en voegt ze toe
aan het 'actieve' project. NAPS2 / Canon-software hoeven slechts naar deze map
te scannen — de rest gebeurt automatisch.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional, Set

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import get_config
from .projects import ALLOWED_IMAGE_EXT, ALLOWED_PDF_EXT, Project


# Bestand moet stabiel zijn (grootte verandert niet) voor we 'm pakken —
# voorkomt dat we half-geschreven scans oppikken.
STABILITY_CHECKS = 2
STABILITY_INTERVAL_SEC = 0.5


def _is_supported(path: Path) -> bool:
    return path.suffix.lower() in (ALLOWED_IMAGE_EXT | ALLOWED_PDF_EXT)


def _wait_until_stable(path: Path, timeout: float = 30.0) -> bool:
    """Wacht tot bestandsgrootte enkele cycli niet meer verandert."""
    deadline = time.time() + timeout
    last_size = -1
    stable_count = 0
    while time.time() < deadline:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        if size == last_size and size > 0:
            stable_count += 1
            if stable_count >= STABILITY_CHECKS:
                return True
        else:
            stable_count = 0
            last_size = size
        time.sleep(STABILITY_INTERVAL_SEC)
    return False


class _InboxHandler(FileSystemEventHandler):
    def __init__(self, on_file_ready: Callable[[Path], None]) -> None:
        super().__init__()
        self._on_ready = on_file_ready
        self._seen: Set[str] = set()
        self._lock = threading.Lock()

    def _process(self, path: Path) -> None:
        key = str(path.resolve())
        with self._lock:
            if key in self._seen:
                return
            self._seen.add(key)
        try:
            if not _is_supported(path):
                return
            if not _wait_until_stable(path):
                logger.warning("Bestand werd niet stabiel binnen tijd: {}", path)
                return
            logger.info("Inbox: nieuw bestand klaar voor import: {}", path.name)
            self._on_ready(path)
        finally:
            # Na een tijdje uit de set halen voor eventuele heropleving
            def _forget():
                time.sleep(60)
                with self._lock:
                    self._seen.discard(key)

            threading.Thread(target=_forget, daemon=True).start()

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._process(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._process(Path(event.dest_path))


class InboxWatcher:
    """Achtergrond-thread die de inbox bewaakt.

    Het 'actieve project' wordt extern bijgehouden (UI-staat) en kan op elk
    moment veranderen via :meth:`set_active_project`. Wanneer er geen actief
    project is, blijven nieuwe scans in de inbox staan tot een project wordt
    geselecteerd.
    """

    def __init__(self) -> None:
        self.cfg = get_config()
        self._observer: Optional[Observer] = None
        self._active_project: Optional[Project] = None
        self._lock = threading.Lock()
        self._pending: list[Path] = []

    # --- actief project ---

    def set_active_project(self, project: Optional[Project]) -> None:
        with self._lock:
            self._active_project = project
            if project is not None and self._pending:
                logger.info(
                    "Actief project gezet ({}); {} wachtende scans worden verwerkt.",
                    project.meta.slug, len(self._pending),
                )
                drainable = self._pending[:]
                self._pending.clear()
            else:
                drainable = []
        for f in drainable:
            self._import(f)

    @property
    def active_project(self) -> Optional[Project]:
        return self._active_project

    # --- import-callback ---

    def _import(self, path: Path) -> None:
        with self._lock:
            project = self._active_project
            if project is None:
                self._pending.append(path)
                logger.info(
                    "Geen actief project — scan in wachtrij: {} ({} totaal)",
                    path.name, len(self._pending),
                )
                return
        try:
            page = project.add_page_from_file(path, copy=False)
        except Exception as exc:
            logger.error("Import van {} mislukt: {}", path, exc)
            return

        # Lazy-import om circulaire dependency te vermijden
        try:
            from .pipeline import process_new_page
            process_new_page(project, page, run_ocr=True)
        except Exception as exc:
            logger.error("Pipeline voor pagina {} mislukt: {}", page.id, exc)

    # --- start/stop ---

    def start(self) -> None:
        if self._observer is not None:
            return
        inbox = Path(self.cfg.inbox_dir)
        inbox.mkdir(parents=True, exist_ok=True)
        handler = _InboxHandler(on_file_ready=self._import)
        observer = Observer()
        observer.schedule(handler, str(inbox), recursive=False)
        observer.start()
        self._observer = observer
        logger.info("Inbox-watcher gestart op: {}", inbox)

        # Eerst eventuele bestaande bestanden alvast oppakken
        threading.Thread(target=self._scan_existing, daemon=True).start()

    def _scan_existing(self) -> None:
        time.sleep(1.0)
        for f in sorted(Path(self.cfg.inbox_dir).iterdir()):
            if f.is_file() and _is_supported(f):
                if _wait_until_stable(f, timeout=5.0):
                    self._import(f)

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("Inbox-watcher gestopt.")

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)
