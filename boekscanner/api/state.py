"""Gedeelde app-staat (singleton) — actief project, watcher, etc.

Kept tiny: alleen 'wat is het huidige project' en de inbox-watcher.
Alle persistente data leeft in projects op disk.
"""

from __future__ import annotations

import threading
from typing import Optional

from ..core.projects import Project, ProjectManager
from ..core.watcher import InboxWatcher


class AppState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.manager = ProjectManager()
        self.watcher = InboxWatcher()
        self._active: Optional[Project] = None

    @property
    def active_project(self) -> Optional[Project]:
        return self._active

    def set_active(self, project: Optional[Project]) -> None:
        with self._lock:
            self._active = project
        self.watcher.set_active_project(project)

    def require_active(self) -> Project:
        if self._active is None:
            raise RuntimeError("Geen actief project. Open of maak eerst een project.")
        return self._active


_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state
