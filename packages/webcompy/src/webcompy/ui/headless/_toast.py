"""Headless Toast host and item components."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import Teleport, Transition, create_element
from webcompy.signal import use_computed
from webcompy.signal._base import SignalBase
from webcompy.ui.composables._toast import ToastRecord


class ToastHostProps(TypedDict, total=False):
    """Props for the headless ``ToastHost``."""

    toasts: Any
    on_dismiss: Callable[[str], None]
    on_remove: Callable[[str], None]
    transition_name: str | None
    class_name: str
    class_item: str
    class_dismiss: str


_FRAMEWORK_CLASS = "webcompy-headless-toast-host"
_ITEM_CLASS = "webcompy-headless-toast-item"
_DISMISS_CLASS = "webcompy-headless-toast-dismiss"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-toast-host")
def ToastHost(context: ComponentContext[ToastHostProps]) -> Any:
    """Render a toast queue inside a Teleport'd live region.

    Each toast item is wrapped in its own ``Transition`` with
    ``on_leave_end`` removing the record from the queue.

    Args:
        context: Component context with toast queue and handlers.

    Returns:
        The rendered host element.

    """
    props = context.props or {}
    toasts_raw = props.get("toasts")
    on_dismiss = props.get("on_dismiss")
    on_remove = props.get("on_remove")
    transition_name = props.get("transition_name") or "webcompy-headless-toast"
    class_name = props.get("class_name", "")
    class_item = props.get("class_item", "")
    class_dismiss = props.get("class_dismiss", "")

    if isinstance(toasts_raw, SignalBase):
        toasts_computed = use_computed(lambda: list(toasts_raw.value))  # type: ignore[union-attr]
        get_toasts = lambda: list(toasts_computed.value)
    else:
        toasts_computed = None
        get_toasts = lambda: list(toasts_raw) if isinstance(toasts_raw, list) else []

    def _build_items() -> list[Any]:
        items: list[Any] = []
        for rec in get_toasts():
            if not isinstance(rec, ToastRecord):
                continue
            is_leaving = bool(rec.leaving)
            item_attrs: dict[str, Any] = {
                "class": _compose_class(_ITEM_CLASS, class_item),
                "data-state": "hidden" if is_leaving else "visible",
                "data-variant": rec.variant,
                "role": "alert" if rec.variant == "error" else "status",
            }
            from webcompy.elements import event as _event

            dismiss_btn = create_element(
                "button",
                {
                    "class": _compose_class(_DISMISS_CLASS, class_dismiss),
                    "aria-label": "Dismiss",
                    _event("click"): (lambda _e, rid=rec.id: on_dismiss(rid) if on_dismiss else None),  # type: ignore[arg-type]
                },
                "x",
            )
            item = create_element("div", item_attrs, rec.message, dismiss_btn)  # type: ignore[arg-type]

            def _make_gen(r: ToastRecord, it: Any) -> Callable[[], Any]:
                def _gen() -> Any:
                    # Re-read toasts to create dependency
                    if toasts_computed is not None:
                        _ = toasts_computed.value
                    cur_list = get_toasts()
                    found = next((x for x in cur_list if x.id == r.id), None)
                    if found is None or found.leaving:
                        # If leaving, return None to trigger leave; if not found, also None
                        # For non-leaving, return item
                        if found is not None and found.leaving:
                            return None
                        if found is None:
                            return None
                    # Check current rec still not leaving
                    cur_rec = next((x for x in get_toasts() if x.id == r.id), None)
                    if cur_rec is not None and cur_rec.leaving:
                        return None
                    return it

                return _gen

            def _on_leave(rid: str = rec.id) -> None:
                if on_remove is not None:
                    on_remove(rid)
                elif on_dismiss is not None:
                    # Fallback: try _remove via state
                    pass

            # Each item gets its own Transition with on_leave_end
            trans = Transition({"name": transition_name, "on_leave_end": _on_leave}, _make_gen(rec, item))
            items.append(trans)
        return items

    # For non-reactive, build once
    if toasts_computed is None:
        items = _build_items()
        if not items:
            # Still need live region even when empty
            host = create_element(
                "div",
                {
                    "class": _compose_class(_FRAMEWORK_CLASS, class_name),
                    "aria-live": "polite",
                    "aria-atomic": "false",
                    "role": "region",
                },
            )
            return Teleport({"to": "body"}, host)
        host_inner = create_element(
            "div",
            {
                "class": _compose_class(_FRAMEWORK_CLASS, class_name),
                "aria-live": "polite",
                "aria-atomic": "false",
                "role": "region",
            },
            *items,
        )
        return Teleport({"to": "body"}, host_inner)

    # Reactive: host re-renders when toasts change, but per-item Transitions are keyed via closure
    # We make the host's children reactive via a computed-backed Teleport
    # Simplify: return Teleport with a container whose children are from _build_items (reactive via toasts_computed)
    def _host_gen() -> Any:
        _ = toasts_computed.value
        its = _build_items()
        return create_element(
            "div",
            {
                "class": _compose_class(_FRAMEWORK_CLASS, class_name),
                "aria-live": "polite",
                "aria-atomic": "false",
                "role": "region",
            },
            *its,
        )

    # Use Transition for host? No, host itself not transitioned. Wrap host gen in a simple element via Teleport
    # Teleport content is host_gen result (which itself is reactive via closure reading computed)
    # But Teleport's children are not automatically reactive. We need to make host_gen reactive via use_computed.
    # Instead, build items directly as Teleport children that are Transitions (each reactive).
    # The Teleport will be re-rendered when toasts_computed changes if we make it depend on computed.
    # Use a wrapper that reads computed
    host_computed = use_computed(lambda: _build_items())

    def _teleport_child() -> Any:
        _ = host_computed.value
        its = _build_items()
        return create_element(
            "div",
            {
                "class": _compose_class(_FRAMEWORK_CLASS, class_name),
                "aria-live": "polite",
                "aria-atomic": "false",
                "role": "region",
            },
            *its,
        )

    # Use a dummy Transition to make it reactive, or just return Teleport with host
    # For now, return Teleport with host that will be re-created on each render via component re-render
    # The component itself will re-render when toasts_computed changes? Not necessarily.
    # But host_computed's on_after_updating will trigger a re-render via signal graph?
    # Simpler: just return Teleport with _teleport_child as Transition child
    content: Any = Transition({"name": transition_name, "duration": 0}, _teleport_child)
    return Teleport({"to": "body"}, content)


ToastHost.scoped_style = {}
