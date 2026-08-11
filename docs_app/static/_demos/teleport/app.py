from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import Teleport, html, switch
from webcompy.signal import use_state


def _modal(close_handler):
    return Teleport(
        {"to": "body"},
        html.DIV(
            {"class": "demo-modal-backdrop"},
            html.DIV(
                {"class": "demo-modal"},
                html.H2({}, "Teleported Modal"),
                html.P({}, "This modal is rendered as a direct child of <body> via Teleport."),
                html.BUTTON({"id": "close-modal", "@click": close_handler}, "Close"),
            ),
        ),
    )


def _dropdown():
    return Teleport(
        {"to": "body"},
        html.UL(
            {"class": "demo-dropdown"},
            html.LI({"class": "demo-dropdown-item"}, "Dropdown Action 1"),
            html.LI({"class": "demo-dropdown-item"}, "Dropdown Action 2"),
            html.LI({"class": "demo-dropdown-item"}, "Dropdown Action 3"),
        ),
    )


@define_component
def App(_: ComponentContext[None]):
    modal_open = use_state(lambda: False)
    dropdown_open = use_state(lambda: False)

    def _toggle_modal(_ev):
        modal_open.value = not modal_open.value

    def _toggle_dropdown(_ev):
        dropdown_open.value = not dropdown_open.value

    return html.DIV(
        {"class": "teleport-demo"},
        html.H1({}, "Teleport Demo"),
        html.P({}, "The modal and the dropdown below are rendered under <body> via Teleport."),
        html.DIV(
            {"class": "demo-controls"},
            html.BUTTON({"id": "open-modal", "@click": _toggle_modal}, "Open Modal"),
            html.BUTTON({"id": "toggle-dropdown", "@click": _toggle_dropdown}, "Toggle Dropdown"),
        ),
        switch({"case": modal_open, "generator": lambda: _modal(_toggle_modal)}, default=None),
        switch({"case": dropdown_open, "generator": _dropdown}, default=None),
    )


App.scoped_style = {
    ".teleport-demo": {
        "font-family": "sans-serif",
        "padding": "1rem",
    },
    ".demo-controls": {
        "display": "flex",
        "gap": "0.5rem",
        "margin-top": "1rem",
    },
    ".demo-controls button": {
        "padding": "0.5rem 1rem",
        "cursor": "pointer",
    },
    ".demo-modal-backdrop": {
        "position": "fixed",
        "inset": "0",
        "background": "rgba(0, 0, 0, 0.4)",
        "display": "flex",
        "align-items": "center",
        "justify-content": "center",
        "z-index": "1000",
    },
    ".demo-modal": {
        "background": "white",
        "color": "black",
        "padding": "1.5rem",
        "border-radius": "0.5rem",
        "min-width": "20rem",
    },
    ".demo-dropdown": {
        "position": "fixed",
        "top": "6rem",
        "left": "1rem",
        "z-index": "1000",
        "background": "white",
        "color": "black",
        "border": "1px solid #ccc",
        "list-style": "none",
        "padding": "0.5rem",
        "margin": "0",
        "min-width": "12rem",
    },
    ".demo-dropdown-item": {
        "padding": "0.25rem 0.5rem",
    },
}

app = WebComPyApp(root_component=App)
app.run()
