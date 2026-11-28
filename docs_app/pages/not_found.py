from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.elements import html
from webcompy.router import RouterContext
from webcompy.signal import use_state

from ..components.ui import DocsButton


@define_component()
def NotFound(context: ComponentContext[RouterContext]):
    displayed_path = use_state(lambda: "")

    @on_mounted
    def _sync_path():
        displayed_path.value = context.props.path

    context.set_title("NotFound - WebComPy")

    return html.DIV(
        {"class": "page-container"},
        html.SECTION(
            {"class": "not-found-card"},
            html.H1({"class": "not-found-heading"}, "404 - Not Found"),
            html.DIV(
                {"class": "not-found"},
                html.P({}, "The requested path does not exist:"),
                html.PRE({"class": "not-found-path"}, displayed_path),
                html.DIV(
                    {"class": "not-found-actions"},
                    DocsButton({"text": "Back to Home", "to": "/", "variant": "primary"}),
                    DocsButton(
                        {
                            "text": "Browse Documentation",
                            "to": "/documents/getting-started/what-is-webcompy",
                        }
                    ),
                ),
            ),
        ),
    )


NotFound.scoped_style = {
    ".not-found-card": {
        "max-width": "36rem",
        "margin": "var(--space-7) auto",
        "padding": "var(--space-6)",
        "background-color": "var(--color-bg-card)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-md)",
        "text-align": "center",
    },
    ".not-found-heading": {
        "margin": "0 0 var(--space-3) 0",
        "padding-bottom": "var(--space-2)",
        "border-bottom": "2px solid var(--color-accent)",
        "font-size": "var(--font-size-2xl)",
        "color": "var(--color-fg)",
    },
    ".not-found": {
        "color": "var(--color-fg-muted)",
    },
    ".not-found-path": {
        "display": "inline-block",
        "max-width": "100%",
        "overflow-x": "auto",
        "padding": "var(--space-2) var(--space-3)",
        "background-color": "var(--color-bg-elevated)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "color": "var(--color-fg)",
        "font-family": "var(--font-mono)",
        "font-size": "var(--font-size-sm)",
    },
    ".not-found-actions": {
        "display": "flex",
        "flex-wrap": "wrap",
        "justify-content": "center",
        "gap": "var(--space-3)",
        "margin-top": "var(--space-5)",
    },
}
