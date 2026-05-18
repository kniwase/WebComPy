from __future__ import annotations

from abc import abstractmethod
from typing import Any, Literal

from webcompy.signal._base import SignalBase
from webcompy.signal._graph import producer_accessed


class HistoryPort(SignalBase[str]):
    def __init__(self, initial_path: str, *, mode: Literal["hash", "history"]) -> None:
        super().__init__(initial_path)
        self._mode: Literal["hash", "history"] = mode
        self._state: dict[str, Any] | None = None

    @property
    def mode(self) -> Literal["hash", "history"]:
        return self._mode

    @property
    def value(self) -> str:
        producer_accessed(self)
        return self._value

    @property
    @SignalBase._get_event
    def state(self) -> dict[str, Any] | None:
        """Return the current route state.

        Returns:
            State dict associated with the current navigation, or ``None``.
        """
        return self._state

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

    def navigate(self, path: str, state: dict[str, Any] | None = None) -> None:
        """Update the signal value and optionally store route state.

        Does NOT call ``pushState`` — callers are responsible for browser
        history manipulation.

        Args:
            path: Target URL path.
            state: Optional state dict to store alongside the path.
        """
        normalized = path[1:] if self._mode == "hash" and path.startswith("#") else path
        if self._value == normalized and self._state is state:
            return
        self._do_navigate(normalized, state)

    @SignalBase._change_event
    def _do_navigate(self, normalized: str, state: dict[str, Any] | None) -> None:
        self._state = state
        self._value = normalized

    @abstractmethod
    def refresh_from_window(self) -> None:
        """Re-read the current URL from ``window.location`` and update the
        signal value, triggering reactivity.
        """
        ...
