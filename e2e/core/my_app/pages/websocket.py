from webcompy.aio import to_reactive_list
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.realtime import use_websocket
from webcompy.signal import use_computed


def _conn_id(stream) -> str:
    for item in stream.items.value:
        if item.startswith("conn:"):
            return item
    return ""


def _messages(stream) -> list[str]:
    return [item for item in stream.items.value if not item.startswith("conn:")]


@define_component("web-socket-page")
def WebSocketPage(context: ComponentContext[None]):
    context.set_title("WebSocket - E2E")

    ws_a = use_websocket("/ws/echo", reconnect_base_delay=0.2)
    ws_b = use_websocket("/ws/echo", reconnect_base_delay=0.2)
    stream_a = to_reactive_list(ws_a)
    stream_b = to_reactive_list(ws_b)

    state_a = use_computed(lambda: ws_a.state.value.name)
    state_b = use_computed(lambda: ws_b.state.value.name)
    conn_a = use_computed(lambda: _conn_id(stream_a))
    conn_b = use_computed(lambda: _conn_id(stream_b))
    messages_a = use_computed(lambda: _messages(stream_a))
    messages_b = use_computed(lambda: _messages(stream_b))
    last_close_a = use_computed(lambda: "" if ws_a.last_close.value is None else str(ws_a.last_close.value.code))

    def _send() -> None:
        ws_a.send("hello")

    def _kill() -> None:
        ws_a.send("kill")

    return html.DIV(
        {"data-testid": "ws-page"},
        html.H2({}, "WebSocket Tests"),
        html.P({}, "State A: ", html.SPAN({"data-testid": "state-a"}, state_a)),
        html.P({}, "State B: ", html.SPAN({"data-testid": "state-b"}, state_b)),
        html.P({}, "Conn A: ", html.SPAN({"data-testid": "conn-a"}, conn_a)),
        html.P({}, "Conn B: ", html.SPAN({"data-testid": "conn-b"}, conn_b)),
        html.P({}, "Last close A: ", html.SPAN({"data-testid": "last-close-a"}, last_close_a)),
        html.BUTTON({"data-testid": "send-btn", "onclick": _send}, "Send"),
        html.BUTTON({"data-testid": "kill-btn", "onclick": _kill}, "Kill"),
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
