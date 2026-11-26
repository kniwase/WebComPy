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


@define_component("teleport-demo-app")
def TeleportDemo(_: ComponentContext[None]):
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


TeleportDemo.scoped_style = {
    ".teleport-demo": {
        "font-family": "var(--font-sans)",
        "color": "var(--color-fg)",
        "padding": "var(--space-4)",
    },
    ".demo-controls": {
        "display": "flex",
        "gap": "0.5rem",
        "margin-top": "1rem",
    },
    ".demo-controls button, .demo-modal button": {
        "padding": "0.5rem 1rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
    ".demo-modal-backdrop": {
        "position": "fixed",
        "inset": "0",
        "background": "rgba(0, 0, 0, 0.5)",
        "display": "flex",
        "align-items": "center",
        "justify-content": "center",
        "z-index": "1000",
    },
    ".demo-modal": {
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
        "border": "1px solid var(--color-border)",
        "box-shadow": "var(--shadow-lg)",
        "padding": "var(--space-5)",
        "border-radius": "var(--radius-md)",
        "min-width": "min(20rem, calc(100vw - 2rem))",
    },
    ".demo-dropdown": {
        "position": "fixed",
        "top": "6rem",
        "left": "1rem",
        "z-index": "1000",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-md)",
        "box-shadow": "var(--shadow-md)",
        "list-style": "none",
        "padding": "0.5rem",
        "margin": "0",
        "min-width": "12rem",
    },
    ".demo-dropdown-item": {
        "padding": "0.25rem 0.5rem",
    },
}

app = WebComPyApp(root_component=TeleportDemo)
app.run()
