"""WebComPy template engine.

Reserved namespace: the ``__wmdf_`` prefix is used by the markdown
for-expansion pipeline (``MarkdownForElement``) to generate synthetic
context keys (e.g. ``__wmdf_0_item``, ``__wmdf_1_item``). User-supplied
context keys with this prefix MAY collide with framework-generated keys
and cause unexpected behavior.
"""

from __future__ import annotations

import re
import textwrap
from collections.abc import Mapping
from typing import Any

from webcompy.di import inject
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.exception import WebComPyException
from webcompy.ports._keys import MARKDOWN_PORT_KEY
from webcompy.template._ast import (
    AttrSpec,
    TemplateElement,
    TemplateNode,
    TemplateText,
)
from webcompy.template._binder import _to_element, bind_children
from webcompy.template._cache import get_or_compile
from webcompy.template._css_template import css_text, css_text_template
from webcompy.template._holes import (
    Hole,
    LiteralText,
    format_value,
    resolve_holes,
    resolve_var,
    split_text,
)
from webcompy.template._naming import (
    TagResolution,
    kebab_to_pascal,
    kebab_to_snake,
    pascal_to_kebab,
    resolve_tag,
)
from webcompy.template._parser import _DIRECTIVE_ARGS

_DIRECTIVE_PARAGRAPH_PATTERN = re.compile(
    rf"<p>\s*(\{{%\s*(?:if|elif|else|endif|for|endfor)\b{_DIRECTIVE_ARGS}%\}})\s*</p>"
)


def _render_nodes(source: str, context: Mapping[str, Any] | None = None) -> list[ElementChildren]:
    ctx: dict[str, Any] = dict(context) if context else {}
    roots = get_or_compile(source)
    return bind_children(roots, ctx)


def _strip_directive_paragraphs(html: str) -> str:
    return _DIRECTIVE_PARAGRAPH_PATTERN.sub(r"\1", html)


def render_markdown(
    source: str,
    context: Mapping[str, Any] | None = None,
    *,
    heading_ids: bool = False,
    code_blocks: bool = False,
    classes: Mapping[str, str] | None = None,
) -> ElementAbstract:
    from webcompy.template._markdown_for import (
        MarkdownForElement,
        _ForBlock,
        _split_markdown_source,
    )

    ctx: dict[str, Any] = dict(context) if context else {}
    if "\n" in source:
        source = textwrap.dedent(source)
    segments = _split_markdown_source(source, ctx)

    parser = inject(MARKDOWN_PORT_KEY)
    elements: list[ElementAbstract] = []
    for seg in segments:
        if isinstance(seg, _ForBlock):
            elements.append(MarkdownForElement(seg.loop_vars, seg.iterable_path, seg.body_markdown, ctx))
        else:
            html = parser.render(seg.text)
            html = _strip_directive_paragraphs(html)
            nodes = _render_nodes(html, ctx)
            for node in nodes:
                if node is None:
                    continue
                if isinstance(node, str) and not node.strip():
                    continue
                elements.append(_to_element(node))

    if heading_ids or code_blocks or classes:
        from webcompy.template._markdown_transforms import (
            apply_class_map_to_roots,
            apply_heading_ids_to_roots,
            replace_code_blocks_in_roots,
        )

        if heading_ids:
            apply_heading_ids_to_roots(elements)
        if code_blocks:
            replace_code_blocks_in_roots(elements)
        if classes is not None:
            apply_class_map_to_roots(elements, classes)

    if len(elements) == 1:
        return elements[0]
    return FragmentElement(elements)


def render_template(source: str, context: Mapping[str, Any] | None = None) -> Element:
    nodes = _render_nodes(source, context)
    if len(nodes) == 1 and isinstance(nodes[0], Element):
        return nodes[0]
    raise WebComPyException("Template must have exactly one root element")


from webcompy.template._markdown_document import (  # noqa: E402
    HeadingInfo,
    MarkdownDocument,
    load_markdown_document,
)

__all__ = [
    "AttrSpec",
    "HeadingInfo",
    "Hole",
    "LiteralText",
    "MarkdownDocument",
    "TagResolution",
    "TemplateElement",
    "TemplateNode",
    "TemplateText",
    "css_text",
    "css_text_template",
    "format_value",
    "kebab_to_pascal",
    "kebab_to_snake",
    "load_markdown_document",
    "pascal_to_kebab",
    "render_markdown",
    "render_template",
    "resolve_holes",
    "resolve_tag",
    "resolve_var",
    "split_text",
]
