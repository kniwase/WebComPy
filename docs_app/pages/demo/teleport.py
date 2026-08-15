from webcompy.components import ComponentContext, define_component
from webcompy.elements import html

from ...components.demo_display import DemoDisplay
from ...components.ui import DocsSection


@define_component("teleport-demo-page")
def TeleportDemoPage(context: ComponentContext[None]):
    context.set_title("Teleport - WebCompy Demo")
    return html.DIV(
        {"class": "page-container"},
        html.H1({"class": "page-title"}, "Teleport"),
        html.P(
            {"class": "page-lead"},
            "Renders children under a different DOM node than their logical position in the "
            "element tree — the building block for modals, dropdowns, and tooltips.",
        ),
        DemoDisplay({"title": "Teleport", "app_name": "teleport", "demo_path": "/_demos/teleport/app.py"}),
        DocsSection(
            {"heading": "Using Teleport"},
            slots={
                "default": lambda: html.P(
                    {},
                    "Wrap a subtree with Teleport and give it a target selector: "
                    'Teleport({"to": "body"}, *children). The children are mounted under the '
                    "resolved target node instead of their logical parent.",
                )
            },
        ),
        DocsSection(
            {"heading": "Target selection"},
            slots={
                "default": lambda: html.P(
                    {},
                    "The 'to' selector MUST address a stable node that is not produced or removed "
                    "by the application's own rendering — typically 'body' or a static element in "
                    "the host page. If the target is removed externally, the teleported content is "
                    "detached with it; the framework does not re-resolve or recover the target.",
                )
            },
        ),
        DocsSection(
            {"heading": "Server-side rendering"},
            slots={
                "default": lambda: html.P(
                    {},
                    "During SSR and static generation, Teleport emits only a single anchor "
                    "placeholder at its logical position; the teleported content is mounted under "
                    "the target by the browser after hydration.",
                )
            },
        ),
    )


TeleportDemoPage.scoped_style = {
    ".page-title": {
        "font-size": "var(--font-size-2xl)",
        "font-weight": "700",
        "margin-bottom": "var(--space-2)",
    },
    ".page-lead": {
        "color": "var(--color-fg-muted)",
        "margin-bottom": "var(--space-4)",
    },
}
