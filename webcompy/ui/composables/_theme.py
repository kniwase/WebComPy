from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webcompy.signal import Signal
    from webcompy.ui.composables._theme_controller import ThemeController
    from webcompy.ui.theme._theme import Theme


def use_theme() -> tuple[Signal[Theme], ThemeController]:
    from webcompy.di import inject
    from webcompy.ui.composables._theme_controller import ThemeController
    from webcompy.ui.theme._manager import ThemeManager
    from webcompy.ui.theme._theme import THEME_KEY

    manager = inject(THEME_KEY, default=None)
    if manager is None:
        raise LookupError(
            "use_theme() requires a ThemeManager in the active DI scope. Provide one before calling use_theme()."
        )
    if not isinstance(manager, ThemeManager):
        raise TypeError(f"Expected ThemeManager, got {type(manager).__name__}")
    return manager.signal, ThemeController(manager)


__all__ = ["use_theme"]
