"""Abstract syntax tree node dataclasses produced by the template parser."""

from __future__ import annotations

from dataclasses import dataclass, field

from webcompy.template._holes import Hole, LiteralText


@dataclass
class TemplateText:
    """A text node holding literal text and interpolation-style holes.

    Args:
        parts: Interleaved ``LiteralText`` and ``Hole`` parts making up
            the text content.

    Attributes:
        parts: Interleaved ``LiteralText`` and ``Hole`` parts making up
            the text content.

    """

    parts: list[LiteralText | Hole] = field(default_factory=list)


@dataclass
class AttrSpec:
    """A parsed attribute on a template element.

    Args:
        name: Attribute name, including directive prefixes such as ``@``
            (event handlers) and ``:`` (ref/bind).
        value: Interpolated value parts, empty for boolean attributes.
        is_boolean: Whether the attribute was written without a value.

    Attributes:
        name: Attribute name, including directive prefixes.
        value: Interpolated value parts.
        is_boolean: Whether the attribute was written without a value.

    """

    name: str
    value: list[LiteralText | Hole] = field(default_factory=list)
    is_boolean: bool = False


@dataclass
class TemplateElement:
    """An element node with attributes and children.

    Args:
        tag_name: Lower-case tag name.
        attrs: Parsed attribute specs.
        children: Child nodes in source order.

    Attributes:
        tag_name: Lower-case tag name.
        attrs: Parsed attribute specs.
        children: Child nodes in source order.

    """

    tag_name: str
    attrs: list[AttrSpec] = field(default_factory=list)
    children: list[TemplateNode] = field(default_factory=list)


@dataclass
class IfNode:
    branches: list[tuple[str | None, list[TemplateNode]]] = field(default_factory=list)


@dataclass
class ForNode:
    loop_vars: list[str]
    iterable_path: str
    body: list[TemplateNode] = field(default_factory=list)


@dataclass
class IfDirective:
    condition: str


@dataclass
class ElifDirective:
    condition: str


@dataclass
class ElseDirective:
    pass


@dataclass
class EndIfDirective:
    pass


@dataclass
class ForDirective:
    loop_vars: list[str]
    iterable_path: str


@dataclass
class EndForDirective:
    pass


DirectiveToken = IfDirective | ElifDirective | ElseDirective | EndIfDirective | ForDirective | EndForDirective


TemplateNode = TemplateText | TemplateElement | IfNode | ForNode
"""Union of all node types that may appear in a parsed template tree."""
