from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component, on_before_destroy
from webcompy.di import InjectionError, inject
from webcompy.elements import html
from webcompy.ports._keys import DOM_PORT_KEY
from webcompy.router import RouterLink
from webcompy.signal import Signal, use_computed, use_state
from webcompy.ui import Dropdown

from .theme_toggle import ThemeToggle


class _SubPage(TypedDict):
    title: str
    to: str


class _PageRequired(TypedDict):
    title: str


class Page(_PageRequired, total=False):
    to: str
    children: list[_SubPage]


@define_component()
def DocsNavbar(context: ComponentContext[list[Page]]):
    _open_states: dict[int, Signal[bool]] = {}
    _mobile_open = use_state(lambda: False)

    def _get_state(idx: int) -> Signal[bool]:
        if idx not in _open_states:
            _open_states[idx] = Signal(False)
        return _open_states[idx]

    def _close_one(idx: int) -> None:
        _get_state(idx).value = False

    def _toggle(idx: int, ev: Any = None):
        if ev is not None and hasattr(ev, "stopPropagation"):
            ev.stopPropagation()
        for other_idx, state in _open_states.items():
            if other_idx != idx:
                state.value = False
        state = _get_state(idx)
        state.value = not state.value

    def _close_all():
        for state in _open_states.values():
            state.value = False
        _mobile_open.value = False

    def _is_open(idx: int):
        return _get_state(idx).value

    def _toggle_mobile(ev: Any):
        if hasattr(ev, "stopPropagation"):
            ev.stopPropagation()
        _mobile_open.value = not _mobile_open.value

    def _on_click_outside(ev: Any):
        _close_all()

    try:
        dom = inject(DOM_PORT_KEY)
    except InjectionError:
        dom = None

    if dom:
        _remove_click = dom.add_document_event_listener("click", _on_click_outside)

        @on_before_destroy
        def _cleanup():
            _remove_click()

    def _generate_navitem(page: Page, idx: int):
        if "children" in page:
            main = (
                [
                    html.LI(
                        {},
                        RouterLink(
                            to=page["to"],
                            text=[page["title"]],
                            attrs={"role": "menuitem"},
                        ),
                    ),
                    html.LI({}, html.HR({})),
                ]
                if "to" in page
                else []
            )
            items = tuple(
                html.LI(
                    {},
                    RouterLink(
                        to=sub["to"],
                        text=[sub["title"]],
                        attrs={"role": "menuitem", "@click": lambda ev: _close_all()},
                    ),
                )
                for sub in page["children"]
            )
            return html.LI(
                {"class": "navbar-item-dropdown"},
                Dropdown(
                    {
                        "open": _get_state(idx),
                        "on_close": lambda idx=idx: _close_one(idx),
                        "class_trigger": "navbar-dropdown-toggle",
                        "class_menu": "navbar-dropdown",
                        "render_closed": True,
                    },
                    slots={
                        "trigger": lambda idx=idx: html.SPAN({}, page["title"]),
                        "default": lambda: [*main, *items],
                    },
                ),
            )
        if "to" in page:
            return html.LI(
                {"class": "navbar-item"},
                RouterLink(
                    to=page["to"],
                    text=[page["title"]],
                    attrs={"@click": lambda ev: _close_all()},
                ),
            )
        return None

    return html.NAV(
        {"class": "navbar"},
        html.DIV(
            {"class": "navbar-inner"},
            html.SPAN({"class": "navbar-brand"}, "WebComPy"),
            html.DIV(
                {"class": "navbar-right"},
                html.DIV(
                    {
                        "id": "navbarNav",
                        "class": use_computed(lambda: "navbar-nav open" if _mobile_open.value else "navbar-nav"),
                    },
                    html.UL(
                        {"class": "navbar-list"},
                        *tuple(_generate_navitem(page, idx) for idx, page in enumerate(context.props)),
                    ),
                ),
                html.BUTTON(
                    {
                        "type": "button",
                        "class": "navbar-mobile-toggle",
                        "aria-controls": "navbarNav",
                        "aria-expanded": use_computed(lambda: "true" if _mobile_open.value else "false"),
                        "aria-label": "Toggle navigation",
                        "@click": _toggle_mobile,
                    },
                    html.SPAN({}, "☰"),
                ),
                ThemeToggle(None),
            ),
        ),
    )


DocsNavbar.scoped_style = {
    " .navbar": {
        "display": "flex",
        "align-items": "center",
        "justify-content": "space-between",
        "padding": "var(--space-3) var(--space-5)",
        "background-color": "var(--color-bg)",
        "border-bottom": "1px solid var(--color-border)",
        "box-shadow": "var(--shadow-sm)",
        "position": "relative",
    },
    " .navbar-inner": {
        "display": "flex",
        "align-items": "center",
        "justify-content": "space-between",
        "width": "100%",
        "max-width": "1200px",
        "margin": "0 auto",
    },
    " .navbar-brand": {
        "font-size": "var(--font-size-xl)",
        "font-weight": "700",
        "color": "var(--color-fg)",
        "margin-right": "var(--space-6)",
        "letter-spacing": "-0.02em",
    },
    " .navbar-right": {
        "display": "flex",
        "align-items": "center",
        "gap": "var(--space-3)",
        "margin-left": "auto",
    },
    " .navbar-mobile-toggle": {
        "display": "none",
        "background": "none",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "padding": "var(--space-2)",
        "width": "2.5rem",
        "height": "2.5rem",
        "font-size": "var(--font-size-lg)",
        "cursor": "pointer",
        "color": "var(--color-fg)",
        "transition": "background-color 0.2s ease",
        "text-align": "center",
        "line-height": "1",
    },
    " .navbar-mobile-toggle:hover": {
        "background-color": "var(--color-bg-elevated)",
    },
    " .navbar-list": {
        "display": "flex",
        "list-style": "none",
        "margin": "0",
        "padding": "0",
        "gap": "var(--space-1)",
        "align-items": "center",
    },
    " .navbar-item": {
        "position": "relative",
    },
    " .navbar-item-dropdown": {
        "position": "relative",
    },
    " .navbar-list a": {
        "display": "block",
        "padding": "var(--space-2)",
        "text-decoration": "none",
        "color": "var(--color-fg)",
        "font-size": "var(--font-size-base)",
        "font-weight": "500",
        "cursor": "pointer",
        "border-radius": "var(--radius-sm)",
        "transition": "background-color 0.15s ease, color 0.15s ease",
    },
    " .navbar-list a:hover": {
        "background-color": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
    },
    " .navbar-list a[aria-expanded='true']": {
        "background-color": "var(--color-bg-elevated)",
    },
    " @media (max-width: 768px)": {
        " .navbar-inner": {
            "flex-wrap": "wrap",
        },
        " .navbar-brand": {
            "order": "1",
        },
        " .navbar-right": {
            "order": "2",
        },
        " .navbar-mobile-toggle": {
            "display": "block",
        },
        " .navbar-nav": {
            "display": "none",
        },
        " .navbar-nav.open": {
            "display": "contents",
        },
        " .navbar-list": {
            "flex-direction": "column",
            "position": "absolute",
            "top": "calc(100% + 1px)",
            "left": "0",
            "right": "0",
            "background-color": "var(--color-bg)",
            "border-bottom": "1px solid var(--color-border)",
            "border-top": "1px solid var(--color-border)",
            "padding": "var(--space-3) var(--space-5)",
            "gap": "0",
            "box-shadow": "var(--shadow-md)",
            "z-index": "999",
        },
        " .navbar-item,  .navbar-item-dropdown": {
            "width": "100%",
        },
        " .navbar-list a": {
            "padding": "var(--space-3) 0",
            "border-radius": "0",
        },
    },
}
