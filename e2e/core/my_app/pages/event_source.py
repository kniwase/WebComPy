from webcompy.aio import to_reactive_list
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.realtime import use_event_source
from webcompy.signal import use_computed


@define_component()
def EventSourcePage(context: ComponentContext[None]):
    context.set_title("EventSource - E2E")

    es_a = use_event_source("/sse/events", events=("message", "session"))
    es_b = use_event_source("/sse/events", events=("message", "session"))
    stream_a = to_reactive_list(es_a)
    stream_b = to_reactive_list(es_b)

    state_a = use_computed(lambda: es_a.state.value.name)
    state_b = use_computed(lambda: es_b.state.value.name)

    def _session(stream) -> str:
        for ev in stream.items.value:
            if ev.event == "session":
                return ev.data
        return ""

    def _messages(stream) -> list[str]:
        return [ev.data for ev in stream.items.value if ev.event == "message"]

    session_a = use_computed(lambda: _session(stream_a))
    session_b = use_computed(lambda: _session(stream_b))
    messages_a = use_computed(lambda: _messages(stream_a))
    messages_b = use_computed(lambda: _messages(stream_b))

    return html.DIV(
        {"data-testid": "sse-page"},
        html.H2({}, "EventSource Tests"),
        html.P(
            {},
            "State A: ",
            html.SPAN({"data-testid": "state-a"}, state_a),
        ),
        html.P(
            {},
            "State B: ",
            html.SPAN({"data-testid": "state-b"}, state_b),
        ),
        html.P(
            {},
            "Session A: ",
            html.SPAN({"data-testid": "session-a"}, session_a),
        ),
        html.P(
            {},
            "Session B: ",
            html.SPAN({"data-testid": "session-b"}, session_b),
        ),
        html.H3({}, "Consumer A"),
        html.UL(
            {"data-testid": "messages-a"},
            repeat(sequence=messages_a, template=lambda m: html.LI({"data-testid": "message-a-item"}, m)),
        ),
        html.H3({}, "Consumer B"),
        html.UL(
            {"data-testid": "messages-b"},
            repeat(sequence=messages_b, template=lambda m: html.LI({"data-testid": "message-b-item"}, m)),
        ),
    )
