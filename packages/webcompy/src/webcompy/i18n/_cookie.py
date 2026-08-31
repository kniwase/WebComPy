"""Read and write the locale cookie through the cookie port."""

from __future__ import annotations

from webcompy.di import inject
from webcompy.i18n._types import I18N_COOKIE_MAX_AGE, I18N_COOKIE_NAME
from webcompy.ports._keys import COOKIE_PORT_KEY


def read_locale_cookie_value() -> str | None:
    """Return the locale stored in the cookie, or ``None`` when unset.

    Returns ``None`` when the ``CookiePort`` is not available in the
    current DI scope or the cookie value is empty.
    """
    port = inject(COOKIE_PORT_KEY, default=None)
    if port is None:
        return None
    raw = port.get(I18N_COOKIE_NAME)
    if not raw:
        return None
    return raw


def write_locale_cookie_value(locale: str) -> None:
    """Persist the locale in the cookie.

    Args:
        locale: Locale to persist.

    """
    port = inject(COOKIE_PORT_KEY, default=None)
    if port is None:
        return
    port.set(
        I18N_COOKIE_NAME,
        locale,
        max_age=I18N_COOKIE_MAX_AGE,
        path="/",
        samesite="Lax",
    )
