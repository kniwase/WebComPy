import random

from my_app.rpc_schema import AddParams, TickerParams, add, ticker
from webcompy.aio import to_reactive_list
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.rpc import RpcWsClient
from webcompy.signal import use_computed, use_state


@define_component()
def RpcWsPage(context: ComponentContext[None]):
    context.set_title("RPC WebSocket - E2E")

    client = RpcWsClient(reconnect_base_delay=0.2)
    state = use_computed(lambda: client.state.value.name)
    result = use_state(lambda: "")

    ticker_id = f"t{random.random()}"
    sub = ticker(client, TickerParams(ticker_id=ticker_id))
    events = to_reactive_list(sub)
    seqs = use_computed(lambda: [event["seq"] for event in events.items.value])
    count = use_computed(lambda: len(seqs.value))

    async def _call(_) -> None:
        try:
            value = await add(client, AddParams(a=2, b=3))
            result.value = f"ok:{value}"
        except Exception as err:
            result.value = f"err:{err}"

    async def _close(_) -> None:
        try:
            # use low-level notify via transport for _webcompy.close (outside contracts)
            await client.notify("_webcompy.close")
        except Exception as err:
            result.value = f"close-err:{err}"

    return html.DIV(
        {"data-testid": "rpc-ws-page"},
        html.H2({}, "RPC WebSocket Tests"),
        html.P({}, "State: ", html.SPAN({"data-testid": "rpc-ws-state"}, state)),
        html.P({}, "Call result: ", html.SPAN({"data-testid": "rpc-ws-result"}, result)),
        html.BUTTON({"data-testid": "rpc-ws-call-btn", "@click": _call}, "Call add"),
        html.BUTTON({"data-testid": "rpc-ws-close-btn", "@click": _close}, "Close"),
        html.P({}, "Event count: ", html.SPAN({"data-testid": "rpc-ws-count"}, count)),
        html.UL(
            {"data-testid": "rpc-ws-events"},
            repeat(sequence=seqs, template=lambda seq: html.LI({"data-testid": "rpc-ws-seq"}, str(seq))),
        ),
    )
