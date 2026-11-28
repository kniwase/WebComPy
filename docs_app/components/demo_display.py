from typing import NotRequired, TypedDict

from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import use_state
from webcompy.ui.code_block import CodeBlock
from webcompy.utils import strip_multiline_text

from .ui import DocsCard


class DemoComponentProps(TypedDict):
    title: str
    app_name: str
    demo_path: str
    peer_demo: NotRequired[bool]
    new_tab_href: NotRequired[str]


def _demo_iframe(app_name: str, title: str):
    return html.IFRAME(
        {
            "class": "demo-iframe",
            "title": title,
            "src": f"/_demos/standard.html?app={app_name}",
            "data-demo-auto-resize": "true",
        }
    )


@define_component()
def DemoDisplay(context: ComponentContext[DemoComponentProps]):
    source_code = use_state(lambda: "")

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

    def _render_demo_body():
        app_name = context.props["app_name"]
        if not context.props.get("peer_demo"):
            return _demo_iframe(app_name, context.props["title"])
        actions = ()
        new_tab_href = context.props.get("new_tab_href")
        if new_tab_href:
            actions = (
                html.DIV(
                    {"class": "demo-peer-actions"},
                    html.A(
                        {
                            "class": "demo-new-tab-link",
                            "href": new_tab_href,
                            "target": "_blank",
                            "rel": "noopener noreferrer",
                        },
                        "Open demo in new tab",
                    ),
                ),
            )
        return html.DIV(
            {"class": "demo-peer-container"},
            html.DIV(
                {"class": "demo-peer-grid"},
                html.DIV(
                    {"class": "demo-peer-pane"},
                    html.DIV({"class": "demo-peer-label"}, "Window A"),
                    _demo_iframe(app_name, "Window A"),
                ),
                html.DIV(
                    {"class": "demo-peer-pane"},
                    html.DIV({"class": "demo-peer-label"}, "Window B"),
                    _demo_iframe(app_name, "Window B"),
                ),
            ),
            *actions,
        )

    return html.DIV(
        {"class": "demo-display-root"},
        html.H2({"class": "demo-display-title"}, context.props["title"]),
        DocsCard(
            {"title": "Demo"},
            slots={"default": _render_demo_body},
        ),
        DocsCard(
            {"title": "Code"},
            slots={"default": lambda: CodeBlock({"code": source_code, "lang": "python", "copyable": True})},
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
