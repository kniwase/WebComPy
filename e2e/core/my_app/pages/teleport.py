from webcompy.components import ComponentContext, define_component
from webcompy.elements import Teleport, html, switch
from webcompy.signal import use_state


def _modal():
    return html.DIV(
        {"data-testid": "teleport-modal", "class": "e2e-teleport-modal"},
        html.H3({}, "Teleported Modal"),
        html.P({}, "modal-content"),
    )


@define_component()
def TeleportPage(context: ComponentContext[None]):
    context.set_title("Teleport - E2E")
    open_state = use_state(lambda: False)

    def _toggle(_ev):
        open_state.value = not open_state.value

    return html.DIV(
        {"data-testid": "teleport-page"},
        html.H2({}, "Teleport Tests"),
        html.P({"data-testid": "before-marker"}, "before-marker"),
        Teleport({"to": "body"}, html.DIV({"data-testid": "static-teleport"}, "static-content")),
        Teleport({"to": "body"}, html.DIV({"data-testid": "static-teleport-2"}, "static-content-2")),
        switch({"case": open_state, "generator": lambda: Teleport({"to": "body"}, _modal())}, default=None),
        html.P({"data-testid": "after-marker"}, "after-marker"),
        html.BUTTON({"data-testid": "toggle-modal", "@click": _toggle}, "Toggle Modal"),
    )


TeleportPage.scoped_style = {
    " .e2e-teleport-modal": {
        "position": "fixed",
        "top": "1rem",
        "right": "1rem",
        "background": "white",
        "color": "black",
        "border": "1px solid black",
        "padding": "1rem",
        "z-index": "1000",
    }
}
