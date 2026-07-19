from __future__ import annotations

from html.parser import HTMLParser

from webcompy.exception import WebComPyException
from webcompy.template._ast import (
    AttrSpec,
    TemplateElement,
    TemplateNode,
    TemplateText,
)
from webcompy.template._holes import split_text

VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "keygen",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

REJECTED_TAGS = frozenset(
    {
        "script",
        "style",
        "iframe",
        "noembed",
        "noframes",
        "xmp",
    }
)


def _reject_tag(tag: str) -> None:
    raise WebComPyException(
        f"<{tag}> is not allowed in templates. Use scoped_style() for CSS or raw_html() for controlled HTML insertion."
    )


class TemplateTreeBuilder(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self._source = source
        self._stack: list[TemplateElement] = []
        self._roots: list[TemplateNode] = []

    @property
    def roots(self) -> list[TemplateNode]:
        return self._roots

    def error(self, message: str) -> None:
        raise WebComPyException(f"Template parse error: {message} (source: {self._source!r})")

    def _current(self) -> TemplateElement | None:
        return self._stack[-1] if self._stack else None

    def _make_attr_spec(self, name: str, value: str | None) -> AttrSpec:
        if value is None or value == "":
            return AttrSpec(name=name, value=[], is_boolean=True)
        return AttrSpec(name=name, value=split_text(value), is_boolean=False)

    def _push_element(self, tag_name: str, attrs: list[AttrSpec]) -> TemplateElement:
        element = TemplateElement(tag_name=tag_name, attrs=attrs, children=[])
        if self._stack:
            self._stack[-1].children.append(element)
        else:
            self._roots.append(element)
        return element

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in REJECTED_TAGS:
            _reject_tag(tag_lower)
        attr_specs = [self._make_attr_spec(n, v) for n, v in attrs]
        if tag_lower in VOID_ELEMENTS:
            self._push_element(tag_lower, attr_specs)
        else:
            element = self._push_element(tag_lower, attr_specs)
            self._stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in REJECTED_TAGS:
            _reject_tag(tag_lower)
        attr_specs = [self._make_attr_spec(n, v) for n, v in attrs]
        self._push_element(tag_lower, attr_specs)

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if not self._stack:
            return
        if self._stack[-1].tag_name == tag_lower:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        parts = split_text(data)
        if not parts:
            return
        text_node = TemplateText(parts=parts)
        if self._stack:
            self._stack[-1].children.append(text_node)
        else:
            self._roots.append(text_node)

    def handle_comment(self, data: str) -> None:
        return


def parse_template(source: str) -> list[TemplateNode]:
    builder = TemplateTreeBuilder(source)
    builder.feed(source)
    builder.close()
    return builder.roots
