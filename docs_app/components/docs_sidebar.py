from collections.abc import Callable
from typing import TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterLink
from webcompy.signal import Signal, use_computed

from ..docs_manifest import DOCS_SECTIONS


class DocsSidebarProps(TypedDict, total=False):
    on_link_click: Callable[..., None]


@define_component
def DocsSidebar(context: ComponentContext[DocsSidebarProps]):
    open_states: dict[int, Signal[bool]] = {}

    def _section_state(idx: int) -> Signal[bool]:
        if idx not in open_states:
            open_states[idx] = Signal(True)
        return open_states[idx]

    def _toggle_section(idx: int, _ev):
        state = _section_state(idx)
        state.value = not state.value

    def _on_link_click(_ev):
        callback = context.props.get("on_link_click")
        if callback is not None:
            callback()

    sections = tuple(
        html.DIV(
            {"class": "docs-sidebar-section"},
            html.BUTTON(
                {
                    "type": "button",
                    "class": "docs-sidebar-section-toggle",
                    "aria-expanded": use_computed(lambda idx=idx: "true" if _section_state(idx).value else "false"),
                    "@click": lambda ev, idx=idx: _toggle_section(idx, ev),
                },
                section["title"],
            ),
            html.UL(
                {
                    "class": "docs-sidebar-links",
                    "style": use_computed(
                        lambda idx=idx: f"display: {'block' if _section_state(idx).value else 'none'};"
                    ),
                },
                *tuple(
                    html.LI(
                        {},
                        RouterLink(
                            to=page["path"],
                            text=[page["label"]],
                            active_class="docs-sidebar-active",
                            attrs={"@click": _on_link_click},
                        ),
                    )
                    for page in section["pages"]
                ),
            ),
        )
        for idx, section in enumerate(DOCS_SECTIONS)
    )
    return html.NAV({"class": "docs-sidebar-nav", "aria-label": "Documentation"}, *sections)


DocsSidebar.scoped_style = {
    " .docs-sidebar-nav": {
        "font-size": "var(--font-size-sm)",
    },
    " .docs-sidebar-section": {
        "margin-bottom": "var(--space-4)",
    },
    " .docs-sidebar-section-toggle": {
        "display": "block",
        "width": "100%",
        "text-align": "left",
        "background": "none",
        "border": "none",
        "padding": "var(--space-2)",
        "font-size": "var(--font-size-sm)",
        "font-weight": "700",
        "color": "var(--color-fg)",
        "cursor": "pointer",
        "border-radius": "var(--radius-sm)",
    },
    " .docs-sidebar-section-toggle:hover": {
        "background-color": "var(--color-bg-elevated)",
    },
    " .docs-sidebar-links": {
        "list-style": "none",
        "margin": "0",
        "padding": "0",
    },
    " .docs-sidebar-links li": {
        "margin": "0",
    },
    " .docs-sidebar-links a": {
        "display": "block",
        "padding": "var(--space-2)",
        "color": "var(--color-fg-muted)",
        "text-decoration": "none",
        "border-radius": "var(--radius-sm)",
    },
    " .docs-sidebar-links a:hover": {
        "background-color": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
    },
    " .docs-sidebar-links a.docs-sidebar-active": {
        "color": "var(--color-link)",
        "font-weight": "600",
        "background-color": "var(--color-bg-elevated)",
    },
}
