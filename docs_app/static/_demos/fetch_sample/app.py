import asyncio
from typing import TypedDict

from webcompy import logging
from webcompy.aio import AsyncWrapper, resolve_async
from webcompy.ajax import HttpClient
from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.signal import ReactiveList, Signal


class User(TypedDict):
    id: int
    name: str


@define_component
def App(context: ComponentContext[None]):
    users = ReactiveList[User]([])
    json_text = Signal("")
    queue = asyncio.Queue[str](maxsize=1)

    @AsyncWrapper()
    async def fetch_user_data(url: str):
        res = await HttpClient.get(url)
        logging.info(res)
        users.value = res.json()["data"]

    @AsyncWrapper()
    async def async_test():
        res = await HttpClient.get("/_demos/fetch_sample/sample.json")
        await queue.put(res.text)

    @context.on_after_rendering
    def _():
        fetch_user_data("/_demos/fetch_sample/sample.json")
        async_test()
        resolve_async(queue.get(), json_text.set_value)

    return html.DIV(
        {},
        html.DIV(
            {},
            html.H5(
                {},
                "User Data",
            ),
            repeat(
                sequence=users,
                template=lambda user_data: html.DIV(
                    {"class": "user-data"},
                    html.UL(
                        {},
                        html.LI({}, "User ID: " + str(user_data["id"])),
                        html.LI({}, "User Name: " + user_data["name"]),
                    ),
                ),
            ),
        ),
        html.DIV(
            {},
            html.H5(
                {},
                "Response Data",
            ),
            html.PRE(
                {},
                html.CODE(
                    {},
                    json_text,
                ),
            ),
        ),
    )


App.scoped_style = {
    ".user-data": {
        "margin": "10px auto",
        "padding": "10px",
        "background-color": "#fafafa",
        "border-radius": "15px",
    },
}

app = WebComPyApp(root_component=App)
app.run()
