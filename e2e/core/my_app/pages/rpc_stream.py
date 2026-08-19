from collections.abc import AsyncIterator

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.rpc import RpcWsClient
from webcompy.rpc import stream as rpc_stream
from webcompy.signal import use_state


@define_component("rpc-stream-page")
def RpcStreamPage(context: ComponentContext[None]):
    context.set_title("RPC Streaming - E2E")

    client = RpcWsClient(reconnect_base_delay=0.2)
    status = use_state(lambda: "idle")
    items = use_state(lambda: [])
    message = use_state(lambda: "")

    async def _consume(source: AsyncIterator[object]) -> None:
        status.value = "running"
        items.value = []
        message.value = ""
        collected: list[str] = []
        try:
            async for item in source:
                collected.append(str(item))
                items.value = list(collected)
            status.value = "closed"
        except Exception as err:
            message.value = str(err)
            status.value = "failed"

    async def _http(_) -> None:
        await _consume(await rpc_stream("count_up", {"n": 5}, result_type=int))

    async def _http_sync(_) -> None:
        await _consume(await rpc_stream("count_up_sync", {"n": 3}, result_type=int))

    async def _http_error(_) -> None:
        await _consume(await rpc_stream("fail_midway", {"n": 5}, result_type=int))

    async def _ws(_) -> None:
        await _consume(await client.stream("count_up", {"n": 5}, result_type=int))

    async def _ws_error(_) -> None:
        await _consume(await client.stream("fail_midway", {"n": 5}, result_type=int))

    return html.DIV(
        {"data-testid": "rpc-stream-page"},
        html.H2({}, "RPC Streaming Tests"),
        html.P({}, "Status: ", html.SPAN({"data-testid": "rpc-stream-status"}, status)),
        html.P({}, "Message: ", html.SPAN({"data-testid": "rpc-stream-message"}, message)),
        html.BUTTON({"data-testid": "rpc-stream-http-btn", "@click": _http}, "HTTP stream"),
        html.BUTTON({"data-testid": "rpc-stream-http-sync-btn", "@click": _http_sync}, "HTTP sync stream"),
        html.BUTTON({"data-testid": "rpc-stream-http-error-btn", "@click": _http_error}, "HTTP error stream"),
        html.BUTTON({"data-testid": "rpc-stream-ws-btn", "@click": _ws}, "WS stream"),
        html.BUTTON({"data-testid": "rpc-stream-ws-error-btn", "@click": _ws_error}, "WS error stream"),
        html.UL(
            {"data-testid": "rpc-stream-items"},
            repeat(sequence=items, template=lambda item: html.LI({"data-testid": "rpc-stream-item"}, str(item))),
        ),
    )
