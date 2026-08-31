"""``use_i18n`` composable resolving the locale signal, translator, and controller from DI."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webcompy.i18n._controller import I18nController
    from webcompy.signal import Signal


def use_i18n() -> tuple[Signal[str], Callable[..., str], I18nController]:
    """Resolve the reactive locale signal, translator, and controller from DI.

    Requires an ``I18nManager`` to have been provided under ``I18N_KEY``
    in the active DI scope.

    Returns:
        A ``(locale, t, controller)`` triple: the reactive ``Signal[str]``
        holding the locale, the translation function, and an
        ``I18nController`` bound to the same manager.

    Raises:
        LookupError: If no i18n manager is registered in the active DI
            scope.
        TypeError: If the injected value is not an ``I18nManager``.

    """
    from webcompy.di import inject
    from webcompy.i18n._controller import I18nController
    from webcompy.i18n._manager import I18nManager
    from webcompy.i18n._types import I18N_KEY

    manager = inject(I18N_KEY, default=None)
    if manager is None:
        raise LookupError(
            "use_i18n() requires an I18nManager in the active DI scope. "
            "Provide one under I18N_KEY before calling use_i18n()."
        )
    if not isinstance(manager, I18nManager):
        raise TypeError(f"Expected I18nManager, got {type(manager).__name__}")
    return manager.locale, manager.t, I18nController(manager)


__all__ = ["use_i18n"]
