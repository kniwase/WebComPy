from __future__ import annotations

from typing import Literal

from webcompy.ports._history import HistoryPort


class ServerHistoryPort(HistoryPort):
    def __init__(self, *, mode: Literal["hash", "history"], initial_path: str = "/") -> None:
        super().__init__(initial_path, mode=mode)

    def current_search(self) -> str:
        return ""

    def history_state(self) -> object | None:
        return self._state

    def refresh_from_window(self) -> None:
        pass
