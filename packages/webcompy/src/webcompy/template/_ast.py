from __future__ import annotations

from dataclasses import dataclass, field

from webcompy.template._holes import Hole, LiteralText


@dataclass
class TemplateText:
    parts: list[LiteralText | Hole] = field(default_factory=list)


@dataclass
class AttrSpec:
    name: str
    value: list[LiteralText | Hole] = field(default_factory=list)
    is_boolean: bool = False


@dataclass
class TemplateElement:
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
