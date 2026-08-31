"""Themed Tabs component composing the headless Tabs with token styling."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._tabs import TabItem
from webcompy.ui.headless._tabs import Tabs as HeadlessTabs
from webcompy.ui.headless._tabs import TabsProps as HeadlessTabsProps


class ThemedTabsProps(TypedDict, total=False):
    """Props accepted by the themed ``Tabs`` component."""

    tabs: list[TabItem]
    active: str
    on_select: Callable[[str], None]
    aria_label: str
    class_name: str
    class_tablist: str
    class_tab: str
    class_panel: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-tabs")
def Tabs(context: ComponentContext[ThemedTabsProps]) -> Any:
    """Render themed tabs with token-based defaults.

    Composes the headless ``Tabs`` and supplies the default
    ``webcompy-tabs*`` classes whose rules live in the shipped primitives
    stylesheet inside the ``components`` layer. Panel switching is instant
    by design (inactive panels stay mounted and hidden); visual effects
    can be attached to the ``data-state`` attributes through the part
    class hooks. Behavior, accessibility, and class pass-through are
    inherited from the headless component; user classes are appended
    after the themed defaults so user rules win at equal specificity.
    The ``active`` prop accepts a signal-like object as well as a plain
    string (forwarded to the headless component unchanged).

    Args:
        context: Component context carrying the ``tabs``, ``active``,
            ``on_select``, ``aria_label``, and class pass-through props.

    Returns:
        The rendered themed tabs element.

    """
    props = context.props or {}
    headless_props: HeadlessTabsProps = {
        "tabs": props.get("tabs", []),  # type: ignore[typeddict-item]
        "on_select": props.get("on_select"),  # type: ignore[typeddict-item]
        "aria_label": props.get("aria_label", ""),
        "class_name": _compose_class("webcompy-tabs", props.get("class_name", "")),
        "class_tablist": _compose_class("webcompy-tabs-tablist", props.get("class_tablist", "")),
        "class_tab": _compose_class("webcompy-tabs-tab", props.get("class_tab", "")),
        "class_panel": _compose_class("webcompy-tabs-panel", props.get("class_panel", "")),
    }
    # Omit the key entirely when not supplied so the headless component
    # can enter its uncontrolled mode.
    active_prop = props.get("active")
    if active_prop is not None:
        headless_props["active"] = active_prop
    return HeadlessTabs(headless_props)
