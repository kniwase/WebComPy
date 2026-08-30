"""DI key, cookie constants, and catalog type aliases for i18n."""

from __future__ import annotations

from webcompy.di._key import InjectKey

I18N_KEY: InjectKey[object] = InjectKey[object]("webcompy-i18n")
"""DI key under which an application provides its ``I18nManager``."""

I18N_COOKIE_NAME = "webcompy-locale"
"""Name of the cookie persisting the active locale."""

I18N_COOKIE_MAX_AGE = 31_536_000
"""Lifetime of the locale cookie in seconds (one year)."""
