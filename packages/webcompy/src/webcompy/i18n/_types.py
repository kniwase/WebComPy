"""DI key, cookie constants, locale normalization helpers, and catalog type aliases for i18n."""

from __future__ import annotations

from collections.abc import Iterable

from webcompy.di._key import InjectKey

I18N_KEY: InjectKey[object] = InjectKey[object]("webcompy-i18n")
"""DI key under which an application provides its ``I18nManager``."""

I18N_COOKIE_NAME = "webcompy-locale"
"""Name of the cookie persisting the active locale."""

I18N_COOKIE_MAX_AGE = 31_536_000
"""Lifetime of the locale cookie in seconds (one year)."""


def language_part(locale: str) -> str:
    """Return the language subtag of a locale tag.

    Args:
        locale: Locale tag such as ``"de-AT"``.

    Returns:
        The portion before the first ``-`` (``"de"``), or the whole
        input when no region subtag is present.

    """
    return locale.split("-", 1)[0] if "-" in locale else locale


def match_supported(locale: str, supported: Iterable[str]) -> str | None:
    """Match a locale against the supported set deterministically.

    An exact case-insensitive tag match wins; otherwise the first
    supported candidate whose language subtag matches wins. Candidates
    are compared in sorted order so every process and interpreter picks
    the same candidate for the same inputs, keeping server rendering and
    browser hydration in agreement even when several supported locales
    share a language.

    Args:
        locale: Locale value to normalize (e.g. from a cookie).
        supported: Locales the application can render.

    Returns:
        The chosen candidate in its original form, or ``None`` when no
        supported locale matches.

    """
    candidates = sorted(c for c in supported if c and c.strip())
    lowered = locale.strip().lower()
    if not lowered or not candidates:
        return None
    for candidate in candidates:
        if candidate.lower() == lowered:
            return candidate
    language = language_part(lowered)
    for candidate in candidates:
        if language_part(candidate).lower() == language:
            return candidate
    return None
