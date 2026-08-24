"""``ThemeController``, the user-facing theme control surface from ``use_theme``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from webcompy.ui.theme._theme import Theme

if TYPE_CHECKING:
    from webcompy.ui.theme._manager import ThemeManager


class ThemeController:
    """User-facing controls over the active theme returned by ``use_theme``.

    Args:
        manager: Theme manager the controller operates on.

    """

    def __init__(self, manager: ThemeManager) -> None:
        self._manager = manager

    def set(self, theme: Theme) -> None:
        """Set the active theme.

        Args:
            theme: Theme to activate.

        """
        self._manager.set(theme)

    def toggle(self) -> None:
        """Toggle between light and dark, resolving ``SYSTEM`` against the OS preference."""
        self._manager.toggle()

    def cycle(self) -> None:
        """Advance the theme through light, dark, then system, wrapping around."""
        self._manager.cycle()
