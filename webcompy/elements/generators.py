from __future__ import annotations

from collections.abc import Callable
from typing import (
    Any,
    NewType,
    TypeAlias,
    TypedDict,
    TypeVar,
    overload,
)

from webcompy.elements.typealias._element_property import (
    AttrValue,
    ElementChildren,
    EventHandler,
)
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.types._element import Element, ElementBase
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements.types._repeat import MultiLineTextElement, RepeatElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import NewLine, TextElement
from webcompy.signal import SignalBase

T = TypeVar("T")
K = TypeVar("K", str, int)
V = TypeVar("V")

EventKey = NewType("EventKey", str)
DomNodeRefKey = NewType("DomNodeRefKey", str)
noderef = DomNodeRefKey(":ref")


def event(event_name: str):
    return EventKey(f"@{event_name}")


def create_element(
    tag_name: HtmlTags,
    /,
    attributes: dict[str | EventKey | DomNodeRefKey, AttrValue | EventHandler | DomNodeRef],
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
            attrs[name] = value  # type: ignore[assignment]
    return Element(tag_name, attrs, events, ref, children)


ChildNode: TypeAlias = ElementBase | TextElement | MultiLineTextElement | NewLine | SignalBase[Any] | str | None
NodeGenerator: TypeAlias = Callable[[], ChildNode]


@overload
def repeat(
    sequence: SignalBase[dict[K, V]],
    template: Callable[[V], ChildNode],
) -> RepeatElement: ...


@overload
def repeat(
    sequence: SignalBase[dict[K, V]],
    template: Callable[[V, K], ChildNode],
) -> RepeatElement: ...


@overload
def repeat(
    sequence: SignalBase[list[V]],
    template: Callable[[V], ChildNode],
) -> RepeatElement: ...


@overload
def repeat(
    sequence: SignalBase[list[V]],
    template: Callable[[V, int], ChildNode],
) -> RepeatElement: ...


@overload
def repeat(
    sequence: SignalBase[list[V]],
    template: Callable[[V, K], ChildNode],
    key: Callable[[V], K],
) -> RepeatElement: ...


def repeat(
    sequence: SignalBase[dict[K, V]] | SignalBase[list[V]],
    template: Callable[[V], ChildNode] | Callable[[V, K], ChildNode],
    key: Callable[[V], K] | None = None,
) -> RepeatElement:
    return RepeatElement(sequence, template, key)  # type: ignore[arg-type]


class SwitchCase(TypedDict):
    case: SignalBase[Any]
    generator: NodeGenerator


def switch(
    *cases: SwitchCase,
    default: NodeGenerator | None = None,
):
    return SwitchElement(
        [(case["case"], case["generator"]) for case in cases],
        default,
    )


def text(text: str | SignalBase[Any], enable_multiline: bool = True):
    if enable_multiline:
        return MultiLineTextElement(text)
    else:
        return TextElement(text)


def break_line():
    return NewLine()
