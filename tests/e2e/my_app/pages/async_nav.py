from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component, useAsync
from webcompy.elements import html
from webcompy.reactive import Reactive


@define_component
def AsyncNavPage(context: ComponentContext[None]):
    context.set_title("Async Nav - E2E")

    message = Reactive("Loading...")
    item_count = Reactive(0)

    async def fetch_data():
        res = await HttpClient.get("async_nav_data.json")
        data = res.json()
        message.value = data["message"]
        item_count.value = len(data["items"])

    useAsync(fetch_data)

    return html.DIV(
        {"data-testid": "async-nav-page"},
        html.H2({}, "Async Navigation Test"),
        html.P({}, "Message: ", html.SPAN({"data-testid": "async-message"}, message)),
        html.P({}, "Items: ", html.SPAN({"data-testid": "async-item-count"}, item_count)),
    )
