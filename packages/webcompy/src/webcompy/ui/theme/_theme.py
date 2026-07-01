from __future__ import annotations

from enum import StrEnum

from webcompy.di._key import InjectKey


class Theme(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


THEME_KEY: InjectKey[object] = InjectKey[object]("webcompy-ui-theme")
THEME_COOKIE_NAME = "webcompy-theme"
THEME_COOKIE_MAX_AGE = 31_536_000
