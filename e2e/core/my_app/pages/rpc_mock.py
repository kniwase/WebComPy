from my_app.rpc_schema import MockAddParams, mock_add
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.rpc import RpcHttpClient
from webcompy.signal import use_state


@define_component("rpc-mock-page")
def RpcMockPage(context: ComponentContext[None]):
    """Page demonstrating browser-side mock of fetch and RPC via middleware."""

    context.set_title("RPC Mock - E2E")

    fetch_result = use_state(lambda: "pending")
    rpc_result = use_state(lambda: "pending")

    async def call_fetch(_) -> None:
        response = await HttpClient.get("/api/mock-echo")
        fetch_result.value = response.text

    async def call_rpc(_) -> None:
        result = await mock_add(RpcHttpClient(), MockAddParams(a=10, b=32))
        rpc_result.value = str(result)

    return html.DIV(
        {},
        html.H1({}, "RPC Mock"),
        html.BUTTON(
            {"@click": call_fetch, "data-testid": "mock-fetch-button"},
            "Call fetch",
        ),
        html.DIV(
            {"data-testid": "mock-fetch-result"},
            html.SPAN({}, "Fetch: "),
            html.SPAN({}, fetch_result),
        ),
        html.BUTTON(
            {"@click": call_rpc, "data-testid": "mock-rpc-button"},
            "Call RPC",
        ),
        html.DIV(
            {"data-testid": "mock-rpc-result"},
            html.SPAN({}, "RPC: "),
            html.SPAN({}, rpc_result),
        ),
    )
