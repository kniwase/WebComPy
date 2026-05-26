from typing import TypedDict

from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import Signal
from webcompy.utils import strip_multiline_text

from .syntax_highlighting import SyntaxHighlighting


class DemoComponentProps(TypedDict):
    title: str
    app_name: str
    demo_path: str


@define_component
def DemoDisplay(context: ComponentContext[DemoComponentProps]):
    source_code = Signal("")

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

    @context.on_after_rendering
    def _():
        load()

    return html.DIV(
        {"class": "demo-display-root"},
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
                        SyntaxHighlighting({"code": source_code, "lang": "python"}),
                    ),
                ),
            ),
        ),
    )


DemoDisplay.scoped_style = {
    ".demo-display-root": {
        "padding-top": "1rem",
    },
    ".card-title": {
        "padding-bottom": "8px",
        "border-bottom": "1px solid #dee2e6",
        "margin-bottom": "16px",
    },
}
