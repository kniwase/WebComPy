"""Read and write the theme preference cookie through the cookie port."""

from __future__ import annotations

from webcompy.di import inject
from webcompy.ports._keys import COOKIE_PORT_KEY
from webcompy.ui.theme._theme import THEME_COOKIE_MAX_AGE, THEME_COOKIE_NAME, Theme


def read_theme_cookie_value() -> Theme | None:
    """Return the theme stored in the cookie, or ``None`` when unset.

    Returns ``None`` when the ``CookiePort`` is not available in the
    current DI scope or the cookie value does not match a ``Theme``.
    """
    port = inject(COOKIE_PORT_KEY, default=None)
    if port is None:
        return None
    raw = port.get(THEME_COOKIE_NAME)
    if raw is None:
        return None
    return _parse_theme_value(raw)


def write_theme_cookie_value(theme: Theme) -> None:
    """Persist the theme in the cookie, deleting it for ``Theme.SYSTEM``.

    Args:
        theme: Theme to persist.

    """
    port = inject(COOKIE_PORT_KEY, default=None)
    if port is None:
        return
    if theme is Theme.SYSTEM:
        port.delete(THEME_COOKIE_NAME, path="/")
        return
    port.set(
        THEME_COOKIE_NAME,
        theme.value,
        max_age=THEME_COOKIE_MAX_AGE,
        path="/",
        samesite="Lax",
    )


def _parse_theme_value(value: str) -> Theme | None:
    lowered = value.strip().lower()
    for theme in Theme:
        if theme.value == lowered:
            return theme
    return None
