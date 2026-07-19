from __future__ import annotations

import textwrap
from collections import OrderedDict
from collections.abc import Callable

from webcompy.template._ast import TemplateNode
from webcompy.template._parser import parse_template

_TEMPLATE_CACHE_MAX_SIZE: int = 128
_template_cache: OrderedDict[str, list[TemplateNode]] = OrderedDict()


def _normalize(source: str) -> str:
    dedented = textwrap.dedent(source)
    return dedented.strip()


def get_or_compile(
    source: str,
    parse_fn: Callable[[str], list[TemplateNode]] | None = None,
) -> list[TemplateNode]:
    compile_fn: Callable[[str], list[TemplateNode]] = parse_fn or parse_template
    normalized = _normalize(source)
    cached = _template_cache.get(normalized)
    if cached is not None:
        _template_cache.move_to_end(normalized)
        return cached
    roots = compile_fn(normalized)
    _template_cache[normalized] = roots
    if len(_template_cache) > _TEMPLATE_CACHE_MAX_SIZE:
        _template_cache.popitem(last=False)
    return roots


def clear_cache() -> None:
    _template_cache.clear()
