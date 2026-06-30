from __future__ import annotations

from collections.abc import Mapping, Sequence
from urllib.parse import unquote

from webcompy.ui.theme._theme import THEME_COOKIE_NAME, Theme


def read_theme_from_cookie(
    headers: Mapping[str, str] | Sequence[tuple[str, str]] | None,
) -> Theme:
    if headers is None:
        return Theme.SYSTEM
    cookie_header: str | None = None
    items: Sequence[tuple[str, str]]
    if isinstance(headers, Mapping):
        for key, value in headers.items():
            if key.lower() == "cookie":
                cookie_header = str(value)
                break
    else:
        items = headers
        for key, value in items:
            if key.lower() == "cookie":
                cookie_header = str(value)
                break
    if not cookie_header:
        return Theme.SYSTEM
    for raw in cookie_header.split(";"):
        key, sep, value = raw.strip().partition("=")
        if not sep:
            continue
        if key != THEME_COOKIE_NAME:
            continue
        decoded = unquote(value).strip().lower()
        for theme in Theme:
            if theme.value == decoded:
                return theme
    return Theme.SYSTEM
