from __future__ import annotations

from webcompy.di import inject
from webcompy.signal import Signal
from webcompy.ui._composables._theme_controller import ThemeController
from webcompy.ui.theme._manager import ThemeManager
from webcompy.ui.theme._theme import THEME_KEY, Theme


def use_theme() -> tuple[Signal[Theme], ThemeController]:
    manager = inject(THEME_KEY, default=None)
    if manager is None:
        raise LookupError(
            "use_theme() requires a ThemeManager in the active DI scope. Provide one before calling use_theme()."
        )
    if not isinstance(manager, ThemeManager):
        raise TypeError(f"Expected ThemeManager, got {type(manager).__name__}")
    return manager.signal, ThemeController(manager)


__all__ = [
    "THEME_KEY",
    "Theme",
    "ThemeController",
    "ThemeManager",
    "use_theme",
]
