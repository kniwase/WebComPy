from typing import TypedDict

from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import Signal
from webcompy.ui.code_block import CodeBlock
from webcompy.utils import strip_multiline_text

from .ui import Card


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
        html.H3({"class": "demo-display-title"}, context.props["title"]),
        Card(
            {"title": "Demo"},
            slots={
                "default": lambda: html.IFRAME(
                    {
                        "src": f"/_demos/standard.html?app={context.props['app_name']}",
                        "style": "width:100%; border:none; min-height:400px;",
                    }
                )
            },
        ),
        Card(
            {"title": "Code"},
            slots={"default": lambda: CodeBlock({"code": source_code, "lang": "python"})},
        ),
    )


DemoDisplay.scoped_style = {
    ".demo-display-root": {
        "padding-top": "var(--space-3)",
    },
    ".demo-display-title": {
        "padding-bottom": "var(--space-2)",
        "border-bottom": "1px solid var(--color-border)",
        "margin-bottom": "var(--space-4)",
        "font-size": "var(--font-size-xl)",
        "font-weight": "600",
        "color": "var(--color-fg)",
    },
}
