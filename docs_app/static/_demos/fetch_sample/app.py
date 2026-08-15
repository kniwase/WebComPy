from dataclasses import dataclass

from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.signal import use_reactive_list, use_state


@dataclass
class User:
    id: int
    name: str


@dataclass
class UsersResponse:
    data: list[User]


@define_component("fetch-sample-app")
def FetchSampleApp(context: ComponentContext[None]):
    users = use_reactive_list(lambda: [])
    scalar_text = use_state(lambda: "")
    raw_text = use_state(lambda: "")

    @AsyncWrapper()
    async def fetch_object():
        res = await HttpClient.get("/_demos/fetch_sample/sample_object.json", response_type=UsersResponse)
        users.value = res.data

    @AsyncWrapper()
    async def fetch_array():
        res = await HttpClient.get("/_demos/fetch_sample/sample_array.json", response_type=list[User])
        users.value = res

    @AsyncWrapper()
    async def fetch_scalar():
        count = await HttpClient.get("/_demos/fetch_sample/sample_scalar.json", response_type=int)
        scalar_text.value = f"Total users: {count}"

    @AsyncWrapper()
    async def async_test():
        res = await HttpClient.get("/_demos/fetch_sample/sample_array.json")
        raw_text.value = res.text

    @context.on_after_rendering
    def _():
        fetch_object()
        fetch_array()
        fetch_scalar()
        async_test()

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
                        html.LI({}, "User ID: " + str(user_data.id)),
                        html.LI({}, "User Name: " + user_data.name),
                    ),
                ),
            ),
        ),
        html.DIV(
            {},
            html.H5(
                {},
                "Scalar Data",
            ),
            html.PRE(
                {},
                html.CODE(
                    {},
                    scalar_text,
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
                    raw_text,
                ),
            ),
        ),
    )


FetchSampleApp.scoped_style = {
    ".user-data": {
        "margin": "10px auto",
        "padding": "10px",
        "background-color": "#fafafa",
        "border-radius": "15px",
    },
}

app = WebComPyApp(root_component=FetchSampleApp)
app.run()
