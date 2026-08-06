from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from typing import Any, Literal, Protocol

from webcompy.signal import SignalBase
from webcompy.signal._graph import producer_accessed


class ScrollManager(Protocol):
    def on_push(self, from_path: str, to_path: str) -> None: ...
    def on_pop(self, from_path: str, to_path: str) -> None: ...


class HistoryPort(SignalBase[str]):
    def __init__(self, initial_path: str, *, mode: Literal["hash", "history"]) -> None:
        super().__init__(initial_path)
        self._mode: Literal["hash", "history"] = mode
        self._state: dict[str, Any] | None = None
        self._navigation_callback: Callable[[str, dict[str, Any] | None], None] | None = None
        self._scroll_manager: ScrollManager | None = None
        self._is_pop_dispatch: bool = False

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
        if self._value == normalized and self._state == state:
            return
        old_value = self._value
        self._do_navigate(normalized, state)
        manager = self._scroll_manager
        if manager is not None and not self._is_pop_dispatch:
            manager.on_push(old_value, normalized)

    def set_scroll_manager(self, manager: ScrollManager | None) -> None:
        """Register an object notified on push/pop navigation classification.

        Args:
            manager: An object with ``on_push(from_path, to_path)`` and
                ``on_pop(from_path, to_path)`` methods, or ``None`` to clear.
        """
        self._scroll_manager = manager

    def set_navigation_callback(
        self,
        callback: Callable[[str, dict[str, Any] | None], None] | None,
    ) -> None:
        """Set a callback invoked on popstate events instead of the default
        ``_do_navigate()`` path.

        Args:
            callback: A callable receiving ``(path, state)`` when the browser
                popstate event fires, or ``None`` to clear.
        """
        self._navigation_callback = callback

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
