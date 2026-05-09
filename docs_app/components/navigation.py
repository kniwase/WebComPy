from typing import Any, TypedDict

from webcompy._browser import browser
from webcompy.components import ComponentContext, define_component, on_before_destroy
from webcompy.elements import html
from webcompy.router import RouterLink
from webcompy.signal import Signal, computed


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
    _mobile_open = Signal(False)

    def _get_state(idx: int) -> Signal[bool]:
        if idx not in _open_states:
            _open_states[idx] = Signal(False)
        return _open_states[idx]

    def _toggle(idx: int, ev: Any):
        if hasattr(ev, "stopPropagation"):
            ev.stopPropagation()
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

    if browser:
        browser.document.addEventListener("click", _on_click_outside)

        @on_before_destroy
        def _cleanup():
            browser.document.removeEventListener("click", _on_click_outside)

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
                    ),
                )
                for sub in page["children"]
            )
            return html.LI(
                {},
                html.A(
                    {
                        "id": f"{menu_id}-toggle",
                        "aria-expanded": computed(lambda idx=idx: "true" if _is_open(idx) else "false"),
                        "aria-haspopup": "true",
                        "aria-controls": menu_id,
                        "@click": lambda ev: _toggle(idx, ev),
                    },
                    page["title"],
                ),
                html.UL(
                    {
                        "id": menu_id,
                        "role": "menu",
                        "style": computed(lambda idx=idx: f"display: {'block' if _is_open(idx) else 'none'};"),
                    },
                    *main,
                    *items,
                ),
            )
        if "to" in page:
            return html.LI(
                {},
                RouterLink(
                    to=page["to"],
                    text=[page["title"]],
                ),
            )
        return None

    return html.NAV(
        {},
        html.DIV(
            {},
            html.SPAN({}, "WebComPy"),
            html.BUTTON(
                {
                    "type": "button",
                    "aria-controls": "navbarNav",
                    "aria-expanded": computed(lambda: "true" if _mobile_open.value else "false"),
                    "aria-label": "Toggle navigation",
                    "@click": _toggle_mobile,
                },
                html.SPAN({}, "☰"),
            ),
            html.DIV(
                {
                    "id": "navbarNav",
                    "style": computed(lambda: f"display: {'block' if _mobile_open.value else 'none'};"),
                },
                html.UL(
                    {},
                    *tuple(_generate_navitem(page, idx) for idx, page in enumerate(context.props)),
                ),
            ),
        ),
    )


Navbar.scoped_style = {
    " nav": {
        "display": "flex",
        "align-items": "center",
        "justify-content": "space-between",
        "padding": "0.5rem 1rem",
        "background-color": "#f8f9fa",
        "border-bottom": "1px solid #dee2e6",
    },
    " nav div": {
        "display": "flex",
        "align-items": "center",
        "width": "100%",
    },
    " nav span": {
        "font-size": "1.25rem",
        "font-weight": "bold",
        "margin-right": "1rem",
    },
    " nav button": {
        "background": "none",
        "border": "1px solid #ccc",
        "padding": "0.25rem 0.5rem",
        "font-size": "1.25rem",
        "cursor": "pointer",
    },
    " nav ul": {
        "display": "flex",
        "list-style": "none",
        "margin": "0",
        "padding": "0",
        "gap": "0.5rem",
    },
    " nav li": {
        "position": "relative",
    },
    " nav li a, nav li a[class]": {
        "display": "block",
        "padding": "0.5rem 1rem",
        "text-decoration": "none",
        "color": "#212529",
        "cursor": "pointer",
    },
    " nav li a:hover": {
        "background-color": "#e9ecef",
    },
    " nav li ul": {
        "position": "absolute",
        "top": "100%",
        "left": "0",
        "background-color": "#fff",
        "border": "1px solid #dee2e6",
        "border-radius": "0.25rem",
        "min-width": "10rem",
        "padding": "0.5rem 0",
        "list-style": "none",
        "z-index": "1000",
    },
    " nav li ul li a": {
        "padding": "0.25rem 1rem",
    },
    " nav li ul hr": {
        "margin": "0.5rem 0",
        "border": "0",
        "border-top": "1px solid #dee2e6",
    },
}
