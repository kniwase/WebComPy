"""Catalog resolution: dot-path keys, interpolation, fallback, and plural selection."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, cast

from webcompy.i18n._plural import get_plural_category

_INTERP_RE = re.compile(r"\{(\w+)\}")


def _language_part(locale: str) -> str:
    return locale.split("-", 1)[0] if "-" in locale else locale


def _interpolate(template: str, params: Mapping[str, Any]) -> str:
    def _sub(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in params:
            return str(params[name])
        return match.group(0)

    return _INTERP_RE.sub(_sub, template)


def resolve_message(
    catalogs: Mapping[str, Mapping[str, object]],
    chain: tuple[str, ...],
    key: str,
) -> str | Mapping[str, str] | None:
    """Resolve ``key`` along the fallback ``chain``, returning the leaf message.

    Walking ``chain`` in order (exact locale, language, fallback locale),
    the first catalog containing ``key`` by dot path wins. Leaf ``Mapping``
    values are plural messages keyed by CLDR categories.

    Args:
        catalogs: Locale-to-catalog mapping.
        chain: Locale fallback chain, most specific first.
        key: Dot-path message key.

    Returns:
        The leaf message, or ``None`` when no catalog in the chain
        provides the key.

    """
    for locale in chain:
        if not locale:
            continue
        catalog = catalogs.get(locale)
        if catalog is None:
            continue
        node: object = catalog
        found = True
        for part in key.split("."):
            if not isinstance(node, Mapping) or part not in node:
                found = False
                break
            node = node[part]
        if found and node is not None:
            if isinstance(node, (str, Mapping)):
                return cast("str | Mapping[str, str]", node)
            return str(node)
    return None


def translate_message(
    catalogs: Mapping[str, Mapping[str, object]],
    chain: tuple[str, ...],
    key: str,
    *,
    count: int | float | None = None,
    params: Mapping[str, Any] | None = None,
) -> str:
    """Translate ``key`` to a string, applying interpolation and pluralization.

    A string leaf interpolates ``{param}`` placeholders, leaving unknown
    placeholders literal. A pipe-shorthand string (``"{count} item|{count}
    items"``) splits into ``one``/``other`` parts when ``count`` is given.
    A dict leaf keys parts by CLDR category, selecting via the plural rules
    for the first element of ``chain``.

    Args:
        catalogs: Locale-to-catalog mapping.
        chain: Locale fallback chain, most specific first.
        key: Dot-path message key.
        count: Count driving plural selection; also interpolated as
            ``{count}`` when provided.
        params: Extra interpolation parameters.

    Returns:
        The translated string, or the key itself when no catalog provides
        it along the chain.

    """
    leaf = resolve_message(catalogs, chain, key)
    if leaf is None:
        return key
    interpolate_params = dict(params or {})
    if count is not None:
        interpolate_params["count"] = count
    if isinstance(leaf, str):
        if count is not None and "|" in leaf:
            one_part, other_part = leaf.split("|", 1)
            category = get_plural_category(chain[0], count)
            return _interpolate(one_part if category == "one" else other_part, interpolate_params)
        return _interpolate(leaf, interpolate_params)
    if count is None:
        template = leaf.get("other")
        if template is None:
            return key
        return _interpolate(template, params or {})
    category = get_plural_category(chain[0], count)
    template = leaf.get(category, leaf.get("other"))
    if template is None:
        return key
    return _interpolate(template, interpolate_params)
