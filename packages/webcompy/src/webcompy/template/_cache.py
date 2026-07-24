from __future__ import annotations

import textwrap
from collections import OrderedDict
from collections.abc import Callable

from webcompy.template._ast import TemplateNode
from webcompy.template._parser import parse_template

_TEMPLATE_CACHE_MAX_SIZE: int = 128
_template_cache: OrderedDict[tuple[str, Callable[[str], list[TemplateNode]]], list[TemplateNode]] = OrderedDict()


def _normalize(source: str) -> str:
    dedented = textwrap.dedent(source)
    return dedented.strip()


def get_or_compile(
    source: str,
    parse_fn: Callable[[str], list[TemplateNode]] | None = None,
) -> list[TemplateNode]:
    compile_fn: Callable[[str], list[TemplateNode]] = parse_fn or parse_template
    normalized = _normalize(source)
    key = (normalized, compile_fn)
    cached = _template_cache.get(key)
    if cached is not None:
        _template_cache.move_to_end(key)
        return cached
    roots = compile_fn(normalized)
    _template_cache[key] = roots
    if len(_template_cache) > _TEMPLATE_CACHE_MAX_SIZE:
        _template_cache.popitem(last=False)
    return roots


def clear_cache() -> None:
    _template_cache.clear()
