"""FastAPI applicatie. Combineert alle routes + serveert de frontend."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .. import __app_name__, __version__
from ..core.config import get_config
from ..core.ocr import check_tesseract
from .schemas import StatusOut
from .state import get_state
from . import routes_export, routes_pages, routes_projects, routes_scan, routes_update


def _web_dir() -> Path:
    """Pad naar HTML/CSS/JS — werkt zowel in dev als gebundeld."""
    if getattr(sys, "frozen", False):
        # In PyInstaller-bundle wijst sys._MEIPASS naar de tijdelijke unpack-dir
        return Path(sys._MEIPASS) / "boekscanner" / "web"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1] / "web"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    cfg = get_config()
    logger.info("BoekScanner v{} start (data dir: {})", __version__, cfg.data_dir)
    state = get_state()
    state.watcher.start()
    yield
    logger.info("BoekScanner sluit af.")
    state.watcher.stop()
    try:
        from ..core.spellcheck import shutdown as spell_shutdown
        spell_shutdown()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=__app_name__,
        version=__version__,
        lifespan=_lifespan,
    )

    # API
    app.include_router(routes_projects.router)
    app.include_router(routes_pages.router)
    app.include_router(routes_scan.router)
    app.include_router(routes_export.router)
    app.include_router(routes_update.router)

    # Status / health
    @app.get("/api/status", response_model=StatusOut)
    def status() -> StatusOut:
        cfg = get_config()
        state = get_state()
        ts = check_tesseract()
        return StatusOut(
            app_version=__version__,
            tesseract_available=ts.available,
            tesseract_version=ts.version,
            tesseract_languages=ts.languages,
            inbox_dir=str(cfg.inbox_dir),
            pending_inbox_files=state.watcher.pending_count,
            active_project=state.active_project.meta.slug if state.active_project else None,
        )

    # Frontend
    web = _web_dir()
    if (web / "static").is_dir():
        app.mount("/static", StaticFiles(directory=str(web / "static")), name="static")

    index_html = web / "templates" / "index.html"
    help_html = web / "templates" / "help.html"

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        if not index_html.is_file():
            return HTMLResponse("<h1>Frontend niet gevonden.</h1>", status_code=500)
        return HTMLResponse(index_html.read_text(encoding="utf-8"))

    @app.get("/help.html", response_class=HTMLResponse)
    def help_page() -> HTMLResponse:
        """Hulp-fragment dat door de frontend in een dialog wordt getoond."""
        if not help_html.is_file():
            return HTMLResponse(
                "<p>Hulppagina niet gevonden. Zie HANDLEIDING.md in de installatiemap.</p>",
                status_code=500,
            )
        return HTMLResponse(help_html.read_text(encoding="utf-8"))

    return app


app = create_app()
