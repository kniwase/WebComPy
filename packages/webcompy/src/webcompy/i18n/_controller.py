"""``I18nController``, the user-facing locale control surface from ``use_i18n``."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webcompy.i18n._manager import I18nManager


class I18nController:
    """User-facing controls over the active locale returned by ``use_i18n``.

    Args:
        manager: I18n manager the controller operates on.

    """

    def __init__(self, manager: I18nManager) -> None:
        self._manager = manager

    @property
    def locale(self) -> str:
        """Currently active locale."""
        return self._manager.value

    def set(self, locale: str) -> None:
        """Set the active locale.

        Args:
            locale: Locale to activate.

        """
        self._manager.set_locale(locale)
