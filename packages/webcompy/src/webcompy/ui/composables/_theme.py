"""``use_theme`` composable resolving the theme signal and controller from DI."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webcompy.signal import Signal
    from webcompy.ui.composables._theme_controller import ThemeController
    from webcompy.ui.theme._theme import Theme


def use_theme() -> tuple[Signal[Theme], ThemeController]:
    """Resolve the reactive theme signal and a ``ThemeController`` from DI.

    Requires a ``ThemeManager`` to have been provided under ``THEME_KEY``
    in the active DI scope.

    Returns:
        A ``(signal, controller)`` pair: the reactive ``Signal[Theme]``
        and a ``ThemeController`` bound to the same manager.

    Raises:
        LookupError: If no theme manager is registered in the active DI
            scope.
        TypeError: If the injected value is not a ``ThemeManager``.

    """
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
