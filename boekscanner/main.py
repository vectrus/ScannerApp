"""Entry-point: start FastAPI in een achtergrond-thread + PyWebView desktop-window.

In `--dev` modus gebruiken we Uvicorn met auto-reload + openen we de browser
i.p.v. PyWebView. Dat maakt UI-iteratie sneller.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser
from contextlib import suppress

import uvicorn
from loguru import logger

from . import __app_name__, __version__
from .api.server import app as fastapi_app
from .core.config import get_config


def _start_uvicorn(host: str, port: int, dev: bool) -> uvicorn.Server:
    config = uvicorn.Config(
        fastapi_app if not dev else "boekscanner.api.server:app",
        host=host,
        port=port,
        log_level="info",
        reload=dev,
        access_log=False,
    )
    server = uvicorn.Server(config)
    return server


def _wait_until_up(url: str, timeout: float = 10.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=__app_name__)
    parser.add_argument("--dev", action="store_true", help="Open in browser i.p.v. desktop-window, met auto-reload.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-window", action="store_true", help="Geen desktop-window — alleen server (handig voor headless test).")
    args = parser.parse_args(argv)

    cfg = get_config()
    host = args.host or cfg.server.host
    port = args.port or cfg.server.port

    logger.info("{} v{} — start op http://{}:{}", __app_name__, __version__, host, port)

    server = _start_uvicorn(host, port, dev=args.dev)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    url = f"http://{host}:{port}/"
    if not _wait_until_up(url):
        logger.error("Server kwam niet op tijd online.")
        return 1

    if args.no_window:
        logger.info("Headless modus — Ctrl+C om te stoppen.")
        try:
            server_thread.join()
        except KeyboardInterrupt:
            pass
        return 0

    if args.dev:
        webbrowser.open(url)
        logger.info("Dev modus — browser geopend. Ctrl+C om te stoppen.")
        try:
            server_thread.join()
        except KeyboardInterrupt:
            pass
        return 0

    # Productie: PyWebView desktop-window
    try:
        import webview  # type: ignore
    except ImportError:
        logger.warning("pywebview niet beschikbaar — open browser i.p.v.")
        webbrowser.open(url)
        try:
            server_thread.join()
        except KeyboardInterrupt:
            pass
        return 0

    window = webview.create_window(
        title=f"{__app_name__}",
        url=url,
        width=1400,
        height=900,
        min_size=(1024, 700),
        confirm_close=False,
    )

    def _on_closed() -> None:
        logger.info("Venster gesloten — server stoppen.")
        server.should_exit = True

    window.events.closed += _on_closed

    with suppress(KeyboardInterrupt):
        webview.start()
    server.should_exit = True
    server_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
