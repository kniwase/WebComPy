"""Themed Collapse component composing the headless Collapse with token styling."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._collapse import Collapse as HeadlessCollapse
from webcompy.ui.headless._collapse import CollapseProps as HeadlessCollapseProps


class ThemedCollapseProps(TypedDict, total=False):
    """Props accepted by the themed ``Collapse`` component."""

    open: bool
    on_toggle: Callable[[bool], None]
    animated: bool
    class_name: str
    class_trigger: str
    class_content: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-collapse")
def Collapse(context: ComponentContext[ThemedCollapseProps]) -> Any:
    """Render a themed collapsible disclosure.

    Composes the headless ``Collapse`` with the default ``webcompy-collapse``
    transition class set. The expand/collapse animation uses the
    grid-template-rows technique (``0fr`` to ``1fr`` on the content element
    with direct children clamped to ``min-height: 0``), which animates to
    natural content height without any JS measurement; headless users can
    substitute their own technique through ``transition_name``. Pass
    ``animated=False`` for instant expansion. Behavior and accessibility
    are inherited from the headless component; user classes are appended
    after the themed defaults so user rules win at equal specificity.
    The ``open`` prop accepts a signal-like object as well as a plain
    boolean (forwarded to the headless component unchanged).

    Args:
        context: Component context carrying the ``open``, ``on_toggle``,
            ``animated``, and class pass-through props, plus the
            ``trigger`` and ``default`` slots.

    Returns:
        The rendered themed collapse element.

    """
    props = context.props or {}
    animated = bool(props.get("animated", True))
    headless_props: HeadlessCollapseProps = {
        "on_toggle": props.get("on_toggle"),  # type: ignore[typeddict-item]
        "transition_name": "webcompy-collapse" if animated else None,
        "class_name": _compose_class("webcompy-collapse", props.get("class_name", "")),
        "class_trigger": _compose_class("webcompy-collapse-trigger", props.get("class_trigger", "")),
        "class_content": _compose_class("webcompy-collapse-content", props.get("class_content", "")),
    }
    # Omit the key entirely when not supplied so the headless component
    # can enter its uncontrolled mode (design D10).
    if props.get("open") is not None:
        headless_props["open"] = props["open"]  # type: ignore[typeddict-unknown-key]
    trigger_content = context.slots("trigger", fallback=lambda: None)
    default_content = context.slots("default", fallback=lambda: None)
    slots: dict[str, Any] = {}
    if trigger_content is not None:
        slots["trigger"] = lambda: trigger_content
    if default_content is not None:
        slots["default"] = lambda: default_content
    return HeadlessCollapse(headless_props, slots=slots)  # type: ignore[call-arg, arg-type]
