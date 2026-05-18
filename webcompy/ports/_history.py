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
    def current_search(self) -> str:
        """Return ``window.location.search`` (query string including ``?``).

        Returns:
            The current query string (``""`` if none).
        """
        ...

    @abstractmethod
    def history_state(self) -> object | None:
        """Return ``window.history.state``.

        Returns:
            The state object associated with the current history entry,
            or ``None``.
        """
        ...

    @abstractmethod
    def navigate(self, path: str) -> None:
        """Push a new entry onto the history stack and update the signal.

        Args:
            path: Target URL path.
        """
        ...

    @abstractmethod
    def refresh_from_window(self) -> None:
        """Re-read the current URL from ``window.location`` and update the
        signal value, triggering reactivity.
        """
        ...
