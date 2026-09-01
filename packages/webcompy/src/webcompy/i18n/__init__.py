"""Internationalization core: locale state, catalogs, pluralization, and SSR resolution."""

from webcompy.i18n._composable import use_i18n
from webcompy.i18n._controller import I18nController
from webcompy.i18n._manager import I18nManager
from webcompy.i18n._plural import register_plural_rule
from webcompy.i18n._server import read_locale_from_cookie, resolve_locale
from webcompy.i18n._types import I18N_KEY

__all__ = [
    "I18N_KEY",
    "I18nController",
    "I18nManager",
    "read_locale_from_cookie",
    "register_plural_rule",
    "resolve_locale",
    "use_i18n",
]
