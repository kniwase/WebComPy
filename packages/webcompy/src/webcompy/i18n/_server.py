"""Server-side locale resolution from request headers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from urllib.parse import unquote

from webcompy.i18n._types import I18N_COOKIE_NAME


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


def _match_supported(locale: str, supported: set[str]) -> str | None:
    lowered = locale.strip().lower()
    exact = sorted(c for c in supported if c.lower() == lowered)
    if exact:
        return exact[0]
    language = lowered.split("-", 1)[0]
    matches = sorted(c for c in supported if c.lower().split("-", 1)[0] == language)
    return matches[0] if matches else None


def _accept_language_pref(headers: Mapping[str, str] | Sequence[tuple[str, str]] | None) -> str | None:
    accept_value = _header_value(headers, "accept-language")
    if accept_value is None:
        return None
    entries: list[tuple[str, float]] = []
    for item in accept_value.split(","):
        item = item.strip()
        if not item:
            continue
        lang, sep, q_part = item.partition(";")
        language = lang.strip()
        if not language:
            continue
        quality = 1.0
        if sep:
            quality_text = q_part.strip()
            if quality_text.startswith("q="):
                try:
                    quality = float(quality_text[2:])
                except ValueError:
                    continue
        entries.append((language, quality))
    entries.sort(key=lambda entry: entry[1], reverse=True)
    return entries[0][0] if entries else None


def resolve_locale(
    headers: Mapping[str, str] | Sequence[tuple[str, str]] | None,
    supported_locales: Iterable[str],
    default_locale: str,
) -> str:
    """Resolve the locale for a request from its headers.

    Resolution order: the locale cookie first, then the Accept-Language
    header's highest-priority locale, then ``default_locale``. A matched
    header entry is mapped back to a supported locale by exact tag or by
    its language part.

    Args:
        headers: Request headers as a mapping or a sequence of
            ``(name, value)`` pairs.
        supported_locales: Locales the application can render.
        default_locale: Fallback locale when neither header matches.

    Returns:
        The resolved locale, always one of ``supported_locales`` or
        ``default_locale``.

    """
    supported = {loc.strip().lower() for loc in supported_locales if loc and loc.strip()}
    cookie_locale = read_locale_from_cookie(headers)
    matched = _match_supported(cookie_locale, supported) if cookie_locale is not None else None
    if matched is not None:
        return matched
    accept_locale = _accept_language_pref(headers)
    matched = _match_supported(accept_locale, supported) if accept_locale is not None else None
    if matched is not None:
        return matched
    return default_locale
