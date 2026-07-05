from webcompy.components import ComponentContext, define_component
from webcompy.elements import ClientOnly, html


@define_component
def ClientOnlyPage(context: ComponentContext[None]):
    context.set_title("ClientOnly - E2E")

    return html.DIV(
        {"data-testid": "client-only-page"},
        html.H2({}, "ClientOnly Tests"),
        html.DIV(
            {"data-testid": "server-content"},
            "This is server-rendered",
        ),
        ClientOnly(
            fallback=lambda: html.DIV({"data-testid": "fallback"}, "Loading browser content..."),
            children=lambda: html.DIV({"data-testid": "browser-content"}, "This is browser-only content"),
        ),
    )
