from __future__ import annotations

from abc import abstractmethod

from webcompy.signal._base import SignalBase
from webcompy.signal._graph import producer_accessed


class HistoryPort(SignalBase[str]):
    def __init__(self, initial_path: str, *, mode: str) -> None:
        super().__init__(initial_path)
        self._mode = mode

    @property
    def value(self) -> str:
        producer_accessed(self)
        return self._value

    @abstractmethod
    def current_search(self) -> str: ...
    @abstractmethod
    def history_state(self) -> object | None: ...
    @abstractmethod
    def navigate(self, path: str) -> None: ...
    @abstractmethod
    def refresh_from_window(self) -> None: ...
