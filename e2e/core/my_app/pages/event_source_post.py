from webcompy.aio import to_reactive_list
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.realtime import use_event_source
from webcompy.signal import use_computed


@define_component()
def EventSourcePostPage(context: ComponentContext[None]):
    context.set_title("EventSource POST - E2E")

    es = use_event_source(
        "/sse-post/post-query",
        method="POST",
        body='{"q":"x"}',
        headers={"Content-Type": "application/json"},
        events=("message",),
    )
    stream = to_reactive_list(es)
    state = use_computed(lambda: es.state.value.name)
    messages = use_computed(lambda: [ev.data for ev in stream.items.value])

    return html.DIV(
        {"data-testid": "sse-post-page"},
        html.H2({}, "EventSource POST Tests"),
        html.P(
            {},
            "State: ",
            html.SPAN({"data-testid": "sse-post-state"}, state),
        ),
        html.H3({}, "Messages"),
        html.UL(
            {"data-testid": "sse-post-messages"},
            repeat(sequence=messages, template=lambda m: html.LI({"data-testid": "sse-post-item"}, m)),
        ),
    )
