from __future__ import annotations
from typing import (
    Any,
    Callable,
    NewType,
    TypeVar,
    TypedDict,
    Union,
)
from typing_extensions import TypeAlias
from webcompy.elements.types._text import TextElement, NewLine
from webcompy.elements.types._element import ElementBase, Element
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements.types._repeat import RepeatElement, MultiLineTextElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.typealias._element_property import (
    AttrValue,
    EventHandler,
    ElementChildren,
)
from webcompy.reactive import ReactiveBase


T = TypeVar("T")

EventKey = NewType("EventKey", str)
_ref = NewType("DomNodeRefKey", str)
noderef = _ref(":ref")


def event(event_name: str):
    return EventKey(f"@{event_name}")


def create_element(
    tag_name: HtmlTags,
    /,
    attributes: dict[str | EventKey | _ref, AttrValue | EventHandler | DomNodeRef],
    *children: ElementChildren,
) -> Element:
    attrs: dict[str, AttrValue] = {}
    events: dict[str, EventHandler] = {}
    ref: DomNodeRef | None = None
    for name, value in attributes.items():
        if isinstance(value, DomNodeRef):
            if name == ":ref":
                ref = value
        elif name.startswith("@") and callable(value):
            events[name[1:]] = value
        else:
            attrs[name] = value
    return Element(tag_name, attrs, events, ref, children)


ChildNode: TypeAlias = Union[
    ElementBase,
    TextElement,
    MultiLineTextElement,
    NewLine,
    ReactiveBase[Any],
    str,
    None,
]
NodeGenerator: TypeAlias = Callable[[], ChildNode]


def repeat(
    sequence: ReactiveBase[list[T]],
    template: Callable[[T], ChildNode],
):
    return RepeatElement(sequence, template)


class SwitchCase(TypedDict):
    case: ReactiveBase[Any]
    generator: NodeGenerator


def switch(
    *cases: SwitchCase,
    default: NodeGenerator | None = None,
):
    return SwitchElement(
        [(case["case"], case["generator"]) for case in cases],
        default,
    )


def text(text: str | ReactiveBase[Any], enable_multiline: bool = True):
    if enable_multiline:
        return MultiLineTextElement(text)
    else:
        return TextElement(text)


def break_line():
    return NewLine()
