from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy.components import TypedComponentBase, component_class, component_template, on_after_rendering
from webcompy.elements import html
from webcompy.reactive import Reactive


@component_class
class AsyncNavPage(TypedComponentBase(props_type=None)):
    def __init__(self):
        self.message = Reactive("Loading...")
        self.item_count = Reactive(0)

    @on_after_rendering
    def after_render(self):
        self._fetch_data()

    @AsyncWrapper()
    async def _fetch_data(self):
        res = await HttpClient.get("async_nav_data.json")
        data = res.json()
        self.message.value = data["message"]
        self.item_count.value = len(data["items"])

    @component_template
    def template(self):
        return html.DIV(
            {"data-testid": "async-nav-page"},
            html.H2({}, "Async Navigation Test"),
            html.P({}, "Message: ", html.SPAN({"data-testid": "async-message"}, self.message)),
            html.P({}, "Items: ", html.SPAN({"data-testid": "async-item-count"}, self.item_count)),
        )
