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


TemplateNode = TemplateText | TemplateElement
