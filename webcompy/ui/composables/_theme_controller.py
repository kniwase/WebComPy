from __future__ import annotations

from typing import TYPE_CHECKING

from webcompy.ui.theme._theme import Theme

if TYPE_CHECKING:
    from webcompy.ui.theme._manager import ThemeManager


class ThemeController:
    def __init__(self, manager: ThemeManager) -> None:
        self._manager = manager

    def set(self, theme: Theme) -> None:
        self._manager.set(theme)

    def toggle(self) -> None:
        self._manager.toggle()

    def cycle(self) -> None:
        self._manager.cycle()
