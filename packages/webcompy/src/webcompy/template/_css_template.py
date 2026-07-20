from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from webcompy.components._generator import StyleDict
from webcompy.template._css_parser import parse_css
from webcompy.template._holes import resolve_holes


def css_text(source: str) -> dict[str, StyleDict]:
    return cast("dict[str, StyleDict]", parse_css(source))


def css_text_template(
    source: str,
    context: dict[str, Any],
) -> Callable[[], dict[str, StyleDict]]:
    def factory() -> dict[str, StyleDict]:
        return cast("dict[str, StyleDict]", parse_css(resolve_holes(source, context)))

    return factory
