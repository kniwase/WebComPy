"""Theme enum, DI key, and theme cookie constants."""

from __future__ import annotations

from enum import StrEnum

from webcompy.di._key import InjectKey


class Theme(StrEnum):
    """Color scheme preference with light, dark, and system variants.

    Each member's value is the string form persisted in the theme cookie.
    """

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


THEME_KEY: InjectKey[object] = InjectKey[object]("webcompy-ui-theme")
"""DI key under which an application provides its ``ThemeManager``."""

THEME_COOKIE_NAME = "webcompy-theme"
THEME_COOKIE_MAX_AGE = 31_536_000
