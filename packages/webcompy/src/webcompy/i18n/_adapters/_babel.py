"""Optional Babel-backed adapter providing full CLDR plural rules.

This module is intentionally not imported by any other framework module.
Projects that add the optional ``babel`` dependency call
``register_babel_plural_rules(...)`` during application startup to replace
the built-in minimal plural-rule table with full CLDR coverage.
"""

from __future__ import annotations

from collections.abc import Iterable


def register_babel_plural_rules(locales: Iterable[str] | None = None) -> None:
    """Register full CLDR plural rules from Babel for the given locales.

    When ``locales`` is omitted, rules are registered for every locale
    Babel knows. Each registration replaces the built-in rule for that
    locale's language, overriding the minimal built-in table.

    Args:
        locales: Locale identifiers to register rules for; defaults to
            all locales available in the Babel installation.

    Raises:
        ImportError: If the optional ``babel`` package is not installed.

    """
    try:
        from babel import Locale  # type: ignore[import-untyped]
        from babel.localedata import locale_identifiers  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "register_babel_plural_rules() requires the optional 'babel' package. "
            "Install it with `uv add babel` before registering the adapter."
        ) from exc

    from webcompy.i18n._plural import register_plural_rule

    targets = tuple(locales) if locales is not None else tuple(locale_identifiers())
    for identifier in targets:
        try:
            locale = Locale.parse(identifier)
        except Exception:
            continue
        forms = locale.plural_forms
        categories = forms.order
        if not categories:
            continue

        def _selector(count: int | float, forms=forms, categories=categories) -> str:
            return categories[forms.plural_form(count)]

        register_plural_rule(identifier, _selector, override=True)
