"""Server-side locale resolution from the request Cookie header."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from urllib.parse import unquote

from webcompy.i18n._types import I18N_COOKIE_NAME, match_supported


def _header_value(
    headers: Mapping[str, str] | Sequence[tuple[str, str]] | None,
    target: str,
) -> str | None:
    if headers is None:
        return None
    if isinstance(headers, Mapping):
        for key, value in headers.items():
            if key.lower() == target:
                return str(value)
        return None
    for key, value in headers:
        if key.lower() == target:
            return str(value)
    return None


def read_locale_from_cookie(
    headers: Mapping[str, str] | Sequence[tuple[str, str]] | None,
) -> str | None:
    """Extract the locale from the Cookie header.

    Args:
        headers: Request headers as a mapping or a sequence of
            ``(name, value)`` pairs.

    Returns:
        The requested locale, or ``None`` when the cookie is absent or
        empty.

    """
    cookie_header = _header_value(headers, "cookie")
    if not cookie_header:
        return None
    for raw in cookie_header.split(";"):
        key, sep, value = raw.strip().partition("=")
        if not sep:
            continue
        if key != I18N_COOKIE_NAME:
            continue
        decoded = unquote(value).strip()
        if decoded:
            return decoded
    return None


def resolve_locale(
    headers: Mapping[str, str] | Sequence[tuple[str, str]] | None,
    supported_locales: Iterable[str],
    default_locale: str,
) -> str:
    """Resolve the locale for a request from its headers.

    Resolution order: the locale cookie if it matches a supported locale
    (exact tag or language part, selected deterministically in sorted
    candidate order), otherwise ``default_locale``. The ``Accept-Language``
    header is deliberately not consulted: server-side negotiation without
    an app-scoped transfer of the resolved value breaks first-render/
    hydration agreement with the browser.

    Args:
        headers: Request headers as a mapping or a sequence of
            ``(name, value)`` pairs.
        supported_locales: Locales the application can render.
        default_locale: Fallback locale when no supported cookie exists.

    Returns:
        The resolved locale, always one of ``supported_locales`` or
        ``default_locale``.

    """
    cookie_locale = read_locale_from_cookie(headers)
    matched = match_supported(cookie_locale, supported_locales) if cookie_locale is not None else None
    if matched is not None:
        return matched
    return default_locale
