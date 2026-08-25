"""Browser scroll management across route navigations."""

from __future__ import annotations

from typing import Any

from webcompy.ports._host import HostPort


class BrowserScrollManager:
    def __init__(self, host: HostPort, window: Any) -> None:
        self._host = host
        self._window = window
        self._positions: dict[str, tuple[int, int]] = {}
        window.history.scrollRestoration = "manual"

    def on_push(self, from_path: str, to_path: str) -> None:
        self._save(from_path)
        self._schedule(0, 0)

    def on_pop(self, from_path: str, to_path: str) -> None:
        self._save(from_path)
        x, y = self._positions.get(to_path, (0, 0))
        self._schedule(x, y)

    def _save(self, path: str) -> None:
        self._positions[path] = (int(self._window.scrollX), int(self._window.scrollY))

    def _schedule(self, x: int, y: int, attempts: int = 3) -> None:
        def apply() -> None:
            doc_height = self._window.document.documentElement.scrollHeight
            viewport_height = self._window.innerHeight
            max_y = max(0, doc_height - viewport_height)
            if y > max_y and attempts > 0:
                self._host.schedule_macro_task(lambda: self._schedule(x, y, attempts - 1))
                return
            self._window.scrollTo(x, min(y, max_y))

        self._host.schedule_macro_task(apply)
