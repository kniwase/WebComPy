from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext

from ..components.ui import Section


@define_component
def NotFound(context: ComponentContext[RouterContext]):
    context.set_title("NotFound - WebCompy")

    return html.DIV(
        {},
        Section(
            {"heading": "404 - Not Found"},
            slots={
                "default": lambda: html.DIV(
                    {"class": "not-found"},
                    html.P({}, "The requested path does not exist:"),
                    html.PRE({"class": "not-found-path"}, context.props.path),
                )
            },
        ),
    )


NotFound.scoped_style = {
    ".not-found": {
        "text-align": "center",
        "padding": "var(--space-5) 0",
        "color": "var(--color-fg-muted)",
    },
    ".not-found-path": {
        "display": "inline-block",
        "padding": "var(--space-2) var(--space-3)",
        "background-color": "var(--color-bg-elevated)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "color": "var(--color-fg)",
        "font-family": "var(--font-mono)",
        "font-size": "var(--font-size-sm)",
    },
}
