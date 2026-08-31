"""Built-in CLDR plural rules and the plural-rule registry.

The registry maps locales to category-selector callables using the CLDR
plural operand model. Locales absent from the table fall back to the
``one``/``other`` Germanic rules with a warning. The opt-in Babel adapter
(``webcompy.i18n._adapters._babel``) registers additional locales through
``register_plural_rule`` without this module importing Babel.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable

from webcompy.i18n._types import language_part

PluralRule = Callable[[int | float], str]
"""Selector mapping a count to its CLDR plural category name."""

_PLURAL_RULES: dict[str, PluralRule] = {}


def _integer_digits(count: int | float) -> int:
    return int(count)


def _fraction_digits(count: int | float) -> int:
    if isinstance(count, int):
        return 0
    text = repr(float(count))
    if "e" in text or "E" in text:
        return 0
    if "." not in text:
        return 0
    return len(text.split(".")[1])


def _one_other_single() -> PluralRule:
    return lambda count: "one" if count == 1 else "other"


def _one_zero_or_single() -> PluralRule:
    return lambda count: "one" if count in (0, 1) else "other"


def _one_zero_to_single() -> PluralRule:
    return lambda count: "one" if 0 <= count <= 1 else "other"


def _one_zero_or_one_integer() -> PluralRule:
    return lambda count: "one" if _integer_digits(count) in (0, 1) and _fraction_digits(count) == 0 else "other"


def _other_only() -> PluralRule:
    return lambda count: "other"


def _russian() -> PluralRule:
    def rule(count: int | float) -> str:
        i = _integer_digits(count)
        v = _fraction_digits(count)
        if v == 0 and i % 10 == 1 and i % 100 != 11:
            return "one"
        if v == 0 and 2 <= i % 10 <= 4 and not 12 <= i % 100 <= 14:
            return "few"
        if (v == 0 and i % 10 == 0) or (v == 0 and 5 <= i % 10 <= 9) or (v == 0 and 11 <= i % 100 <= 14):
            return "many"
        return "other"

    return rule


def _polish() -> PluralRule:
    def rule(count: int | float) -> str:
        i = _integer_digits(count)
        v = _fraction_digits(count)
        if i == 1 and v == 0:
            return "one"
        if v == 0 and i % 10 in (2, 3, 4) and not 12 <= i % 100 <= 14:
            return "few"
        if (
            (v == 0 and i != 1 and i % 10 in (0, 1))
            or (v == 0 and i % 10 in (5, 6, 7, 8, 9))
            or (v == 0 and 12 <= i % 100 <= 14)
        ):
            return "many"
        return "other"

    return rule


def _czech_slovak() -> PluralRule:
    def rule(count: int | float) -> str:
        i = _integer_digits(count)
        v = _fraction_digits(count)
        if i == 1 and v == 0:
            return "one"
        if i in (2, 3, 4) and v == 0:
            return "few"
        if v != 0:
            return "many"
        return "other"

    return rule


def _romanian() -> PluralRule:
    def rule(count: int | float) -> str:
        i = _integer_digits(count)
        v = _fraction_digits(count)
        n = abs(count)
        if i == 1 and v == 0:
            return "one"
        if v != 0 or n == 0 or 2 <= n % 100 <= 19:
            return "few"
        return "other"

    return rule


def _hebrew() -> PluralRule:
    def rule(count: int | float) -> str:
        i = _integer_digits(count)
        v = _fraction_digits(count)
        n = abs(count)
        if i == 1 and v == 0:
            return "one"
        if i == 2 and v == 0:
            return "two"
        if v == 0 and not 0 <= n <= 10 and n % 10 == 0:
            return "many"
        return "other"

    return rule


def _arabic() -> PluralRule:
    def rule(count: int | float) -> str:
        n = abs(count)
        if n == 0:
            return "zero"
        if n == 1:
            return "one"
        if n == 2:
            return "two"
        if 3 <= n % 100 <= 10:
            return "few"
        if 11 <= n % 100 <= 99:
            return "many"
        return "other"

    return rule


def _register_builtin(table: dict[str, PluralRule]) -> None:
    for locale in ("en", "de", "nl", "sv", "da", "no", "fi", "hu", "it", "es", "el"):
        table[locale] = _one_other_single()
    for locale in ("fr", "hi"):
        table[locale] = _one_zero_or_single()
    for locale in ("pt",):
        table[locale] = _one_zero_to_single()
    for locale in ("tr",):
        table[locale] = _one_zero_or_one_integer()
    for locale in ("ja", "zh", "ko", "th", "vi", "id"):
        table[locale] = _other_only()
    table["ru"] = _russian()
    table["uk"] = _russian()
    table["pl"] = _polish()
    table["cs"] = _czech_slovak()
    table["sk"] = _czech_slovak()
    table["ro"] = _romanian()
    table["he"] = _hebrew()
    table["ar"] = _arabic()


_register_builtin(_PLURAL_RULES)


def register_plural_rule(locale: str, rule: PluralRule, *, override: bool = False) -> None:
    """Register a plural-rule selector for a locale.

    Locales are matched by their language part (``"de-AT"`` falls back to
    ``"de"``). The built-in table registers at registration time, so the
    Babel adapter or application code can replace or extend entries.

    Args:
        locale: Locale tag the rule applies to.
        rule: Selector mapping a count to a CLDR category name.
        override: Replace an existing registration under the same locale.

    Raises:
        ValueError: If the locale is already registered while ``override``
            is ``False``.

    """
    key = language_part(locale).lower()
    if key in _PLURAL_RULES and not override:
        raise ValueError(
            f"Plural rules for locale {key!r} are already registered. "
            "Pass override=True to replace the existing registration."
        )
    _PLURAL_RULES[key] = rule


def get_plural_category(locale: str, count: int | float) -> str:
    """Return the CLDR plural category for ``count`` under ``locale``.

    Locales absent from the registry fall back to the ``one``/``other``
    rules with a warning.

    Args:
        locale: Locale tag governing the selection.
        count: Count to classify.

    Returns:
        The CLDR category name (e.g. ``"one"``, ``"few"``, ``"many"``).

    """
    language = language_part(locale).lower()
    rule = _PLURAL_RULES.get(language)
    if rule is None:
        warnings.warn(
            f"No plural rules registered for locale {locale!r}; using one/other.",
            stacklevel=2,
        )
        return "one" if count == 1 else "other"
    return rule(count)
