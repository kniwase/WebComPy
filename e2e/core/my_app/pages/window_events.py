from webcompy import use_document_event, use_window_event
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component
def WindowEventsPage(context: ComponentContext[None]):
    context.set_title("Window Events - E2E")

    width, _ = use_window_event("resize", 0, transform=lambda e: e.target.innerWidth)
    hidden, _ = use_document_event(
        "visibilitychange",
        True,
        transform=lambda e: bool(e.target.hidden),
    )

    return html.DIV(
        {"data-testid": "window-events-page"},
        html.H2({}, "Window Events"),
        html.P(
            {},
            "Window width: ",
            html.SPAN({"data-testid": "window-width"}, width),
        ),
        html.P(
            {},
            "Document hidden: ",
            html.SPAN({"data-testid": "document-hidden"}, hidden),
        ),
    )
