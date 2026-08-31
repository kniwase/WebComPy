"""Headless Accordion component composing Collapse items with an open policy."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element
from webcompy.signal import use_computed, use_state
from webcompy.ui.headless._collapse import Collapse, CollapseProps


class AccordionItem(TypedDict):
    """One accordion entry: stable key, trigger label, and content generator."""

    key: str
    label: Any
    content: Callable[[], Any]


class AccordionProps(TypedDict, total=False):
    """Props accepted by the headless ``Accordion`` component."""

    items: list[AccordionItem]
    single_open: bool
    on_toggle: Callable[[str, bool], None]
    transition_name: str | None
    class_name: str
    class_trigger: str
    class_content: str


_FRAMEWORK_CLASS = "webcompy-headless-accordion"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-accordion")
def Accordion(context: ComponentContext[AccordionProps]) -> Any:
    """Render a stack of Collapse items sharing one open-state.

    Each item renders as a headless ``Collapse`` whose open flag is a
    view of the accordion's shared set of open keys, so composition keeps
    Collapse independently useful while the policies apply across items.
    Multi-open is the default; ``single_open=True`` closes the other items
    whenever one opens. Item identity is key-based. ``on_toggle`` is
    invoked with ``(key, is_open)`` for every item whose open state
    changed, including siblings closed by the single-open policy (closures
    first, then openings). Only one level of items is supported; nesting
    accordions deeper is untested and documented as unsupported. The
    ``items`` list is read once at setup; a different item set requires
    remounting. No visual styling is emitted.

    Args:
        context: Component context carrying the ``items``, ``single_open``,
            ``on_toggle``, ``transition_name``, and class pass-through
            props. ``transition_name``, ``class_trigger``, and
            ``class_content`` are forwarded to every composed Collapse.

    Returns:
        The rendered headless accordion element.

    """
    props = context.props or {}
    items: list[AccordionItem] = list(props.get("items") or [])
    keys = [str(item.get("key", "")) for item in items]
    single_open = bool(props.get("single_open", False))
    on_toggle: Callable[[str, bool], None] | None = props.get("on_toggle")
    transition_name = props.get("transition_name")
    class_name = props.get("class_name", "")
    class_trigger = props.get("class_trigger", "")
    class_content = props.get("class_content", "")

    def _empty_open() -> tuple[str, ...]:
        return ()

    open_state = use_state(_empty_open)

    def _is_item_open(key: str) -> bool:
        return key in open_state.value

    def _set_open(key: str, want_open: bool) -> None:
        current = set(open_state.value)
        if want_open:
            current = {key} if single_open else current | {key}
        else:
            current.discard(key)
        old_state = open_state.value
        new_state = tuple(k for k in keys if k in current)
        if new_state == old_state:
            if on_toggle is not None:
                on_toggle(key, want_open)
            return
        open_state.value = new_state
        if on_toggle is not None:
            for closed_key in (k for k in old_state if k not in new_state):
                on_toggle(closed_key, False)
            for opened_key in (k for k in new_state if k not in old_state):
                on_toggle(opened_key, True)

    children: list[Any] = []
    for item in items:
        key = str(item.get("key", ""))
        collapse_props: CollapseProps = {
            "open": use_computed(lambda k=key: k in open_state.value),  # type: ignore[typeddict-item]
            "on_toggle": (lambda k: lambda new_open: _set_open(k, new_open))(key),
            "transition_name": transition_name,
            "class_trigger": class_trigger,
            "class_content": class_content,
        }
        item_content: Callable[[], Any] = item.get("content", lambda: None)  # type: ignore[assignment]
        children.append(
            Collapse(
                collapse_props,  # type: ignore[arg-type]
                slots={
                    "trigger": lambda it=item: it.get("label", ""),
                    "default": lambda fn=item_content: fn(),
                },
            )
        )

    root_attrs: dict[str, Any] = {"class": _compose_class(_FRAMEWORK_CLASS, class_name)}
    return create_element("div", root_attrs, *children)


Accordion.scoped_style = {}
