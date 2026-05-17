from typing import TypedDict

from webcompy import browser
from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component
from webcompy.elements import DomNodeRef, html
from webcompy.signal import Signal
from webcompy.utils import strip_multiline_text


class DemoComponentProps(TypedDict):
    title: str
    app_name: str
    demo_path: str


@define_component
def DemoDisplay(context: ComponentContext[DemoComponentProps]):
    code_ref = DomNodeRef()
    source_code = Signal("")

    source_code.on_after_updating(lambda _: run_highlight())

    @AsyncWrapper()
    async def load():
        if source_code.value and not source_code.value.startswith("# Failed"):
            return
        try:
            res = await HttpClient.get(context.props["demo_path"])
            if res.ok:
                source_code.value = strip_multiline_text(res.text).strip()
            else:
                source_code.value = f"# Failed to load {context.props['demo_path']}"
        except Exception:
            source_code.value = f"# Failed to load {context.props['demo_path']}"

    def run_highlight():
        if browser and code_ref.element and hasattr(browser.window, "hljs"):
            browser.window.hljs.highlightElement(code_ref.element)

    @context.on_after_rendering
    def _():
        load()

    return html.DIV(
        {},
        html.DIV(
            {"class": "card"},
            html.DIV(
                {"class": "card-body"},
                html.H5({"class": "card-title"}, context.props["title"]),
                html.DIV(
                    {"class": "card"},
                    html.DIV(
                        {"class": "card-body"},
                        html.IFRAME(
                            {
                                "src": f"/_demos/standard.html?app={context.props['app_name']}",
                                "style": "width:100%; border:none; min-height:400px;",
                            }
                        ),
                    ),
                ),
                html.BR(),
                html.DIV(
                    {"class": "card"},
                    html.DIV({"class": "card-header"}, "Code"),
                    html.DIV(
                        {"class": "card-body"},
                        html.PRE(
                            {},
                            html.CODE(
                                {
                                    "class": "language-python",
                                    ":ref": code_ref,
                                },
                                source_code,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
