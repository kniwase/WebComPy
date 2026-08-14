from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component, on_before_destroy
from webcompy.di import InjectionError, inject
from webcompy.elements import Teleport, html
from webcompy.events import use_document_event, use_window_event
from webcompy.ports._keys import DOM_PORT_KEY
from webcompy.router import RouterLink
from webcompy.signal import Signal, use_computed, use_readonly_signal, use_state

from .theme_toggle import ThemeToggle


class _SubPage(TypedDict):
    title: str
    to: str


class _PageRequired(TypedDict):
    title: str


class Page(_PageRequired, total=False):
    to: str
    children: list[_SubPage]


@define_component
def Navbar(context: ComponentContext[list[Page]]):
    _open_states: dict[int, Signal[bool]] = {}
    positions, update_positions = use_readonly_signal({})
    _mobile_open = use_state(lambda: False)

    def _get_state(idx: int) -> Signal[bool]:
        if idx not in _open_states:
            _open_states[idx] = Signal(False)
        return _open_states[idx]

    def _toggle(idx: int, ev: Any):
        if hasattr(ev, "stopPropagation"):
            ev.stopPropagation()
        for other_idx, state in _open_states.items():
            if other_idx != idx:
                state.value = False
        state = _get_state(idx)
        state.value = not state.value
        if state.value and dom:
            update_positions(_measure_open_menus())

    def _measure_open_menus() -> dict[int, tuple[float, float]]:
        if not dom:
            return {}
        snap: dict[int, tuple[float, float]] = {}
        for idx, state in _open_states.items():
            if not state.value:
                continue
            toggle_el = dom.get_element_by_id(f"navbar-dropdown-{idx}-toggle")
            if toggle_el is not None:
                rect = toggle_el.getBoundingClientRect()
                snap[idx] = (float(rect.bottom), float(rect.right))
        return snap

    def _measure(_ev: Any) -> dict[int, tuple[float, float]]:
        snap = _measure_open_menus()
        update_positions(snap)
        return snap

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

    _, _ = use_document_event("scroll", {}, transform=_measure)
    _, _ = use_window_event("resize", {}, transform=_measure)

    def _generate_navitem(page: Page, idx: int):
        if "children" in page:
            menu_id = f"navbar-dropdown-{idx}"

            main = (
                [
                    html.LI(
                        {},
                        RouterLink(
                            to=page["to"],
                            text=[page["title"]],
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
                        attrs={"@click": lambda ev: _close_all()},
                    ),
                )
                for sub in page["children"]
            )
            return html.LI(
                {"class": "navbar-item-dropdown"},
                html.A(
                    {
                        "id": f"{menu_id}-toggle",
                        "class": "navbar-dropdown-toggle",
                        "aria-expanded": use_computed(lambda idx=idx: "true" if _is_open(idx) else "false"),
                        "aria-haspopup": "true",
                        "aria-controls": menu_id,
                        "@click": lambda ev: _toggle(idx, ev),
                    },
                    page["title"],
                ),
                Teleport(
                    {"to": "body"},
                    html.UL(
                        {
                            "id": menu_id,
                            "class": "navbar-dropdown",
                            "role": "menu",
                            "style": use_computed(
                                lambda idx=idx: (
                                    f"display: {'block' if _is_open(idx) else 'none'}; "
                                    f"--nav-dropdown-top: {positions.value.get(idx, (0.0, 0.0))[0]}px; "
                                    f"--nav-dropdown-right: {positions.value.get(idx, (0.0, 0.0))[1]}px;"
                                )
                            ),
                        },
                        *main,
                        *items,
                    ),
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


Navbar.scoped_style = {
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
    " .navbar-dropdown": {
        "position": "fixed",
        "top": "var(--nav-dropdown-top)",
        "left": "auto",
        "right": "calc(100vw - var(--nav-dropdown-right))",
        "background-color": "var(--color-bg)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-md)",
        "min-width": "12rem",
        "padding": "var(--space-2) 0",
        "list-style": "none",
        "z-index": "1000",
        "box-shadow": "var(--shadow-md)",
        "margin": "0",
    },
    " .navbar-dropdown a": {
        "padding": "var(--space-2) var(--space-4)",
        "font-size": "var(--font-size-sm)",
        "border-radius": "0",
    },
    " .navbar-dropdown a:hover": {
        "background-color": "var(--color-bg-elevated)",
    },
    " .navbar-dropdown hr": {
        "margin": "var(--space-2) 0",
        "border": "0",
        "border-top": "1px solid var(--color-border)",
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
        " .navbar-dropdown": {
            "left": "0",
            "right": "0",
            "width": "auto",
            "border": "none",
            "border-radius": "0",
            "box-shadow": "none",
            "padding-left": "var(--space-4)",
            "min-width": "auto",
        },
    },
}
