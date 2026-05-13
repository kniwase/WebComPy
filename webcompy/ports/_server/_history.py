from __future__ import annotations

from webcompy.ports._history import HistoryPort


class ServerHistoryPort(HistoryPort):
    def __init__(self, *, mode: str, initial_path: str = "/") -> None:
        super().__init__(initial_path, mode=mode)
        self._state: object | None = None

    def current_search(self) -> str:
        return ""

    def history_state(self) -> object | None:
        return self._state

    def navigate(self, path: str) -> None:
        self._value = path

    def refresh_from_window(self) -> None:
        pass
