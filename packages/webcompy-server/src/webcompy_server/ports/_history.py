"""Server-side history port."""

from __future__ import annotations

from typing import Literal

from webcompy.ports._history import HistoryPort


class ServerHistoryPort(HistoryPort):
    """Server-side history port without browser navigation.

    Args:
        mode: Routing mode.
        initial_path: Initial path.

    """

    def __init__(self, *, mode: Literal["hash", "history"], initial_path: str = "/") -> None:
        super().__init__(initial_path, mode=mode)

    def current_search(self) -> str:
        """Return the current search string.

        Returns:
            Empty string on the server.

        """
        return ""

    def history_state(self) -> object | None:
        """Return the current history state.

        Returns:
            Current state object.

        """
        return self._state

    def refresh_from_window(self) -> None:
        """Sync history state from the window.

        Returns:
            ``None``.

        """
        pass
