"""``I18nManager``: reactive locale state with catalogs, translation, and persistence."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from webcompy.di import inject
from webcompy.i18n._catalog import translate_message
from webcompy.i18n._cookie import read_locale_cookie_value, write_locale_cookie_value
from webcompy.ports._keys import HOST_PORT_KEY
from webcompy.signal import Signal


def _language_part(locale: str) -> str:
    return locale.split("-", 1)[0] if "-" in locale else locale


def _dedupe(chain: tuple[str, ...]) -> tuple[str, ...]:
    seen: list[str] = []
    for item in chain:
        if item and item not in seen:
            seen.append(item)
    return tuple(seen)


class I18nManager:
    """Reactive locale state holding a ``Signal[str]`` and message catalogs.

    The manager resolves the active locale at construction (an explicit
    ``initial_locale``, then the locale cookie in the browser, then the
    browser language, then ``default_locale``) and exposes the translation
    function ``t``, whose reads of the locale signal make template
    interpolations reactive. ``set_locale`` updates the signal and persists
    the choice to the locale cookie.

    Args:
        catalogs: Locale-to-catalog mapping; keys resolve by dot path
            through nested dictionaries.
        default_locale: Locale used when nothing else determines the
            active locale.
        fallback_locale: Locale consulted after the exact locale and its
            language during message lookup; defaults to ``default_locale``.
        supported_locales: Locales the application can render; defaults to
            the catalog keys. Governs normalization and SSR resolution.
        initial_locale: Externally resolved locale (e.g. from SSR request
            headers) that takes priority over cookie/browser defaults.
        persist: Whether ``set_locale`` writes the locale cookie.

    Attributes:
        locale: Reactive signal holding the current locale.

    """

    def __init__(
        self,
        catalogs: Mapping[str, Mapping[str, object]],
        *,
        default_locale: str,
        fallback_locale: str | None = None,
        supported_locales: Iterable[str] | None = None,
        initial_locale: str | None = None,
        persist: bool = True,
    ) -> None:
        self._catalogs = dict(catalogs)
        self._default_locale = default_locale
        self._fallback_locale = fallback_locale or default_locale
        self._supported = set(supported_locales) if supported_locales is not None else set(catalogs)
        self._persist = persist
        self._signal: Signal[str] = Signal(self._resolve_initial(initial_locale))

    def _resolve_initial(self, initial_locale: str | None) -> str:
        if initial_locale is not None:
            return self._normalize(initial_locale)
        cookie_value = read_locale_cookie_value()
        if cookie_value is not None:
            return self._normalize(cookie_value)
        browser_language = self._browser_language()
        if browser_language is not None:
            return self._normalize(browser_language)
        return self._default_locale

    def _normalize(self, locale: str) -> str:
        lowered = locale.strip().lower()
        for candidate in self._supported:
            if candidate.lower() == lowered:
                return candidate
        language = lowered.split("-", 1)[0]
        for candidate in self._supported:
            if candidate.lower().split("-", 1)[0] == language:
                return candidate
        return self._default_locale

    def _browser_language(self) -> str | None:
        host = inject(HOST_PORT_KEY, default=None)
        if host is None:
            return None
        getter = host.create_js_global_getter("navigator")
        try:
            navigator = getter()
        except Exception:
            return None
        if navigator is None:
            return None
        language = getattr(navigator, "language", None)
        return language or None

    @property
    def locale(self) -> Signal[str]:
        """Reactive signal holding the current locale."""
        return self._signal

    @property
    def value(self) -> str:
        """Current locale."""
        return self._signal.value

    @property
    def default_locale(self) -> str:
        """Locale used when nothing else determines the active locale."""
        return self._default_locale

    @property
    def fallback_locale(self) -> str:
        """Locale consulted after the exact locale and its language."""
        return self._fallback_locale

    def t(self, key: str, *, count: int | float | None = None, **params: Any) -> str:
        """Translate ``key`` against the current locale.

        Reads ``locale.value`` at call time, so template interpolations
        using ``t`` re-render when the locale switches.

        Args:
            key: Dot-path message key.
            count: Count driving plural selection; interpolated as
                ``{count}`` when provided.
            **params: Interpolation parameters.

        Returns:
            The translated string, or the key when it is missing along
            the fallback chain.

        """
        locale = self._signal.value
        language = _language_part(locale)
        chain = _dedupe((locale, language, self._fallback_locale))
        return translate_message(self._catalogs, chain, key, count=count, params=params)

    def set_locale(self, locale: str) -> None:
        """Set the active locale, persisting it when persistence is enabled.

        Args:
            locale: Locale to activate.

        """
        normalized = self._normalize(locale)
        self._signal.value = normalized
        if self._persist:
            write_locale_cookie_value(normalized)
