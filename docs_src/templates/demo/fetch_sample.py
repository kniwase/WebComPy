from typing import TypedDict
from webcompy.elements import html, repeat
from webcompy.components import define_component, ComponentContext
from webcompy.reactive import ReactiveList, Reactive
from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy import logging


class User(TypedDict):
    id: int
    name: str


@define_component
def FetchSample(context: ComponentContext[None]):
    users = ReactiveList[User]([])
    json_text = Reactive("")

    @AsyncWrapper()
    async def fetch_user_data():
        res = await HttpClient.get("fetch_sample/sample.json")
        logging.info(res)
        users.value = res.json()["dat"]
        json_text.value = res.text

    @context.on_after_rendering
    def _():
        fetch_user_data()

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


FetchSample.scoped_style = {
    ".user-data": {
        "margin": "10px auto",
        "padding": "10px",
        "background-color": "#fafafa",
        "border-radius": "15px",
    },
}
