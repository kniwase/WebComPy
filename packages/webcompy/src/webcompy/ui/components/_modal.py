"""Themed Modal component composing the headless Modal."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._modal import Modal as HeadlessModal
from webcompy.ui.headless._modal import ModalProps as HeadlessModalProps


class ModalProps(TypedDict, total=False):
    """Props for the themed ``Modal`` component."""

    open: bool
    on_close: Callable[[], None]
    aria_label: str
    aria_labelledby: str
    close_on_backdrop: bool
    close_on_escape: bool
    transition_name: str | None
    class_name: str
    class_backdrop: str
    class_panel: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-modal")
def Modal(context: ComponentContext[ModalProps]) -> Any:
    """Render a themed modal dialog.

    Args:
        context: Component context with modal props.

    Returns:
        The themed modal element.

    """
    props = context.props or {}
    slot_content = context.slots("default", fallback=lambda: None)
    headless_props: HeadlessModalProps = {
        "open": props.get("open", False),  # type: ignore[typeddict-item]
        "on_close": props.get("on_close"),  # type: ignore[typeddict-item]
        "aria_label": props.get("aria_label", ""),  # type: ignore[typeddict-item]
        "aria_labelledby": props.get("aria_labelledby", ""),  # type: ignore[typeddict-item]
        "close_on_backdrop": props.get("close_on_backdrop", True),  # type: ignore[typeddict-item]
        "close_on_escape": props.get("close_on_escape", True),  # type: ignore[typeddict-item]
        "transition_name": props.get("transition_name", "webcompy-modal"),
        "class_name": _compose_class("webcompy-modal", props.get("class_name", "")),
        "class_backdrop": _compose_class("webcompy-modal-backdrop", props.get("class_backdrop", "")),
        "class_panel": _compose_class("webcompy-modal-panel", props.get("class_panel", "")),
    }
    # Forward slots
    slots: dict[str, Any] = {}
    try:
        inner = slot_content
        if inner is not None:
            slots["default"] = lambda: inner
    except Exception:
        pass
    return HeadlessModal(headless_props, slots=slots)  # type: ignore[call-arg, arg-type]
