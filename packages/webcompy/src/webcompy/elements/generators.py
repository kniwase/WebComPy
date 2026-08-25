"""Generator functions building reactive element trees."""

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
from webcompy.elements.types._client_only import ClientOnlyElement
from webcompy.elements.types._element import Element
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements.types._repeat import MultiLineTextElement, RepeatElement
from webcompy.elements.types._suspense import SuspenseElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import NewLine, RawHTMLElement, TextElement
from webcompy.signal import SignalBase

T = TypeVar("T")
K = TypeVar("K", str, int)
V = TypeVar("V")

EventKey = NewType("EventKey", str)
DomNodeRefKey = NewType("DomNodeRefKey", str)
PreserveChildrenKey = NewType("PreserveChildrenKey", str)
noderef = DomNodeRefKey(":ref")
"""Attribute key marking a ``DomNodeRef`` value that captures the element's DOM node."""
preserve_children_key = PreserveChildrenKey(":preserve_children")


def event(event_name: str):
    """Return an attribute key binding an event handler for ``event_name``.

    Use the returned key in an ``create_element`` attribute mapping with a
    callable value to attach a listener for the named DOM event.

    Args:
        event_name: DOM event name such as ``click`` or ``input``.

    Returns:
        Attribute key that routes the corresponding value as an event handler.

    """
    return EventKey(f"@{event_name}")


def create_element(
    tag_name: HtmlTags,
    /,
    attributes: dict[str | EventKey | DomNodeRefKey, AttrValue | EventHandler | DomNodeRef],
    *children: ElementChildren,
) -> Element:
    """Create a reactive element of the given tag.

    Attribute values accept reactive signals that keep the DOM attribute in
    sync, event keys from ``event()`` attach handlers, and ``noderef``
    captures the node in a ``DomNodeRef``.

    Args:
        tag_name: HTML tag name.
        attributes: Mapping of attribute names (plus ``event()``/``noderef``
            keys) to static or reactive values.
        *children: Child elements, strings, or reactive values.

    Returns:
        The configured ``Element`` node.

    """
    attrs: dict[str, AttrValue] = {}
    events: dict[str, EventHandler] = {}
    ref: DomNodeRef | None = None
    preserve = False
    for name, value in attributes.items():
        if isinstance(value, DomNodeRef):
            if name == ":ref":
                ref = value
        elif isinstance(value, bool) and name == ":preserve_children":
            preserve = value
        elif name.startswith("@") and callable(value):
            events[name[1:]] = value
        else:
            attrs[name] = value  # type: ignore[assignment]
    return Element(tag_name, attrs, events, ref, children, preserve_children=preserve)


NodeGenerator: TypeAlias = Callable[[], ElementChildren]


@overload
def repeat(
    sequence: SignalBase[dict[K, V]],
    template: Callable[[V], ElementChildren],
) -> RepeatElement: ...


@overload
def repeat(
    sequence: SignalBase[dict[K, V]],
    template: Callable[[V, K], ElementChildren],
) -> RepeatElement: ...


@overload
def repeat(
    sequence: SignalBase[list[V]],
    template: Callable[[V], ElementChildren],
) -> RepeatElement: ...


@overload
def repeat(
    sequence: SignalBase[list[V]],
    template: Callable[[V, int], ElementChildren],
) -> RepeatElement: ...


@overload
def repeat(
    sequence: SignalBase[list[V]],
    template: Callable[[V, K], ElementChildren],
    key: Callable[[V], K],
) -> RepeatElement: ...


def repeat(
    sequence: SignalBase[dict[K, V]] | SignalBase[list[V]],
    template: Callable[[V], ElementChildren] | Callable[[V, K], ElementChildren],
    key: Callable[[V], K] | None = None,
) -> RepeatElement:
    """Create an element repeating ``template`` for each item of a reactive sequence.

    The sequence may be a ``ReactiveList`` or ``ReactiveDict`` signal. For
    keyed updates, the template receives the key as its second argument and
    ``key`` derives keys for list items; keyed reconciliation reuses DOM
    nodes across updates instead of rebuilding them.

    Args:
        sequence: Reactive list or dict signal providing the items.
        template: Callable building children for one item, optionally
            receiving the key as a second argument.
        key: Callable deriving a stable key from a list item; disallowed
            for dict sequences, which are keyed by definition.

    Returns:
        A ``RepeatElement`` that re-renders as the sequence changes.

    """
    return RepeatElement(sequence, template, key)  # type: ignore[arg-type]


class SwitchCase(TypedDict):
    case: SignalBase[Any]
    generator: NodeGenerator


def switch(
    *cases: SwitchCase,
    default: NodeGenerator | None = None,
):
    """Create an element rendering the first case whose condition is truthy.

    Args:
        *cases: ``SwitchCase`` pairs of a reactive condition and a child
            generator.
        default: Generator rendered when no case condition is truthy.

    Returns:
        A ``SwitchElement`` swapping its children as conditions change.

    """
    return SwitchElement(
        [(case["case"], case["generator"]) for case in cases],
        default,
    )


def suspense(
    *,
    fallback: NodeGenerator,
    children: NodeGenerator,
    error_fallback: NodeGenerator | None = None,
    timeout: float = 10.0,
) -> SuspenseElement:
    """Create an element awaiting async child setup before showing children.

    The fallback renders while children's async setup resolves; on server
    environments resolution block rendering up to ``timeout`` seconds.

    Args:
        fallback: Generator rendered while the children are pending.
        children: Generator producing the content shown once resolved.
        error_fallback: Generator rendered when child async setup raises.
        timeout: Seconds to wait for async resolution before falling back.

    Returns:
        A ``SuspenseElement`` managing the pending/resolved states.

    """
    return SuspenseElement(
        fallback=fallback,
        children=children,
        error_fallback=error_fallback,
        timeout=timeout,
    )


def client_only(
    children: Callable[[], ElementChildren],
    fallback: Callable[[], ElementChildren] | None = None,
) -> ClientOnlyElement:
    """Create an element rendered only in the browser.

    On server rendering and static generation the ``fallback`` (or nothing)
    is emitted instead, keeping browser-only content out of the prerender.

    Args:
        children: Generator producing the browser-only content.
        fallback: Generator producing server-side placeholder content.

    Returns:
        A ``ClientOnlyElement`` switching content by environment.

    """
    return ClientOnlyElement(children, fallback)


def text(text: str | SignalBase[Any], enable_multiline: bool = True):
    """Create a text node element, replacing line breaks with newline elements.

    Args:
        text: Static string or reactive value rendered as text.
        enable_multiline: When ``True`` render each line as a text node
            followed by a ``NewLine``; otherwise render the plain string.

    Returns:
        A ``TextElement`` or ``MultiLineTextElement``.

    """
    if enable_multiline:
        return MultiLineTextElement(text)
    else:
        return TextElement(text)


def raw_html(html: str | SignalBase[Any], *, wrapper: str = "span") -> RawHTMLElement:
    """Create an element injecting raw HTML into a wrapper element.

    Args:
        html: HTML string or reactive value set as ``innerHTML``.
        wrapper: Tag name of the element the HTML is injected into.

    Returns:
        A ``RawHTMLElement`` rendering the raw HTML.

    """
    return RawHTMLElement(html, wrapper=wrapper)


def break_line():
    """Create a line break element.

    Returns:
        A ``NewLine`` element rendering as a ``<br>`` node.

    """
    return NewLine()
