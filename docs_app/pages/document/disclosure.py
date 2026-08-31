"""Disclosure & feedback components documentation page."""

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext
from webcompy.signal import use_state
from webcompy.template import load_markdown_document
from webcompy.ui import Accordion, Alert, Badge, Card, Collapse, Progress, Skeleton, Tabs

from ...components.docs_page import DOCS_PAGE_SCOPED_STYLE, docs_page_template


@define_component()
def DisclosureDemo(context: ComponentContext[None]):
    active_tab = use_state(lambda: "a")
    collapse_open = use_state(lambda: False)
    progress_value = use_state(lambda: 35)

    def _on_collapse_toggle(is_open: bool) -> None:
        collapse_open.value = is_open

    def _bump_progress(_e):
        progress_value.value = min(100.0, float(progress_value.value) + 15)

    tabs = [
        {
            "key": "a",
            "label": "Profile",
            "content": lambda: html.DIV(
                {},
                html.P({}, "Profile panel — type something, switch away and back."),
                html.INPUT({"type": "text", "placeholder": "state survives switches"}),
            ),
        },
        {"key": "b", "label": "Settings", "content": lambda: html.P({}, "Settings panel content.")},
        {"key": "c", "label": "Advanced", "content": lambda: html.P({}, "Advanced panel content.")},
    ]

    items = [
        {"key": "i1", "label": "What is WebComPy?", "content": lambda: html.P({}, "A reactive Python web framework.")},
        {"key": "i2", "label": "Is it fast?", "content": lambda: html.P({}, "Fast enough for docs pages.")},
        {"key": "i3", "label": "Do I need JavaScript?", "content": lambda: html.P({}, "No.")},
    ]

    return html.DIV(
        {"class": "disclosure-demo"},
        html.H3({}, "Tabs"),
        Tabs({"tabs": tabs, "active": active_tab, "on_select": lambda key: setattr(active_tab, "value", key)}),
        html.H3({}, "Collapse"),
        Collapse(
            {"open": collapse_open, "on_toggle": _on_collapse_toggle},
            slots={
                "trigger": lambda: html.SPAN({}, "Show the hidden section"),
                "default": lambda: html.P({}, "This content animated open through the grid-rows technique."),
            },
        ),
        html.H3({}, "Accordion"),
        Accordion({"items": items, "single_open": True}),
        html.H3({}, "Alert"),
        Alert({"variant": "info"}, slots={"default": lambda: html.SPAN({}, "Heads up — informational message.")}),
        Alert({"variant": "success"}, slots={"default": lambda: html.SPAN({}, "Saved successfully.")}),
        Alert(
            {"variant": "error", "dismissable": True},
            slots={"default": lambda: html.SPAN({}, "Something failed — dismiss me.")},
        ),
        html.H3({}, "Progress"),
        Progress({"value": progress_value, "min": 0, "max": 100, "aria_label": "Demo progress"}),
        html.BUTTON({"@click": _bump_progress}, "Bump progress"),
        Progress({"indeterminate": True, "aria_label": "Indeterminate loading"}),
        html.H3({}, "Badge"),
        html.DIV(
            {"class": "disclosure-demo-row"},
            Badge({"variant": "neutral"}, slots={"default": lambda: "neutral"}),
            Badge({"variant": "info"}, slots={"default": lambda: "info"}),
            Badge({"variant": "success"}, slots={"default": lambda: "success"}),
            Badge({"variant": "warning"}, slots={"default": lambda: "warning"}),
            Badge({"variant": "error"}, slots={"default": lambda: "error"}),
        ),
        html.H3({}, "Skeleton"),
        html.DIV(
            {"class": "disclosure-demo-row"},
            Skeleton({"shape": "circle", "width": "3rem", "height": "3rem"}),
            html.DIV(
                {"class": "disclosure-demo-stack"},
                Skeleton({"shape": "line", "width": "60%"}),
                Skeleton({"shape": "line", "width": "80%"}),
            ),
        ),
        html.H3({}, "Card"),
        Card(
            {},
            slots={
                "header": lambda: html.SPAN({}, "Card title"),
                "default": lambda: html.SPAN({}, "Promoted from the docs site's ad-hoc card."),
                "footer": lambda: html.SPAN({}, "Card footer"),
            },
        ),
    )


DisclosureDemo.scoped_style = {
    " .disclosure-demo": {"display": "grid", "gap": "var(--space-3)", "margin": "var(--space-4) 0"},
    " .disclosure-demo-row": {"display": "flex", "gap": "var(--space-2)", "align-items": "center"},
    " .disclosure-demo-stack": {"display": "grid", "gap": "var(--space-2)", "flex": "1"},
    " .disclosure-demo button": {"justify-self": "start"},
}


@define_component()
async def DisclosurePage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/disclosure.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template(doc, context.props.path, extra_content=DisclosureDemo({}))


DisclosurePage.scoped_style = DOCS_PAGE_SCOPED_STYLE
