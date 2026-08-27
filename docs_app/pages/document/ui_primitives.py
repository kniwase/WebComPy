from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document
from webcompy.ui import Spinner
from webcompy.ui.headless import Spinner as HeadlessSpinner

from ...components.docs_page import DOCS_PAGE_SCOPED_STYLE, docs_page_template


@define_component()
def SpinnerShowcase(context: ComponentContext[dict]):
    return html.DIV(
        {"class": "spinner-showcase"},
        html.DIV(
            {"class": "spinner-showcase-row"},
            html.DIV(
                {"class": "spinner-showcase-item"},
                Spinner({"label": "Loading (small)", "size": "sm"}),
                html.SPAN({"class": "spinner-showcase-caption"}, 'size="sm"'),
            ),
            html.DIV(
                {"class": "spinner-showcase-item"},
                Spinner({"label": "Loading (medium)"}),
                html.SPAN({"class": "spinner-showcase-caption"}, 'size="md" (default)'),
            ),
            html.DIV(
                {"class": "spinner-showcase-item"},
                Spinner({"label": "Loading (large)", "size": "lg"}),
                html.SPAN({"class": "spinner-showcase-caption"}, 'size="lg"'),
            ),
        ),
        html.DIV(
            {"class": "spinner-showcase-row"},
            html.DIV(
                {"class": "spinner-showcase-item"},
                HeadlessSpinner(
                    {
                        "label": "Headless Spinner styled by user CSS",
                        "class_name": "docs-headless-spinner-demo",
                    }
                ),
                html.SPAN({"class": "spinner-showcase-caption"}, "headless + class_name"),
            ),
        ),
    )


SpinnerShowcase.scoped_style = {
    " .spinner-showcase": {
        "display": "grid",
        "gap": "var(--space-4)",
        "margin": "var(--space-5) 0 0",
        "padding": "var(--space-4)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-md)",
        "background-color": "var(--color-bg-card)",
    },
    " .spinner-showcase-row": {
        "display": "flex",
        "align-items": "center",
        "gap": "var(--space-5)",
        "flex-wrap": "wrap",
    },
    " .spinner-showcase-item": {
        "display": "flex",
        "align-items": "center",
        "gap": "var(--space-2)",
    },
    " .spinner-showcase-caption": {
        "font-size": "var(--font-size-sm)",
        "color": "var(--color-fg-muted)",
    },
    " .docs-headless-spinner-demo[data-state='loading']": {
        "display": "inline-block",
        "width": "var(--space-5)",
        "height": "var(--space-5)",
        "border": "2px dashed var(--color-border)",
        "border-top-color": "var(--color-accent)",
        "border-radius": "50%",
        "animation": "docs-headless-spin 0.8s linear infinite",
    },
    "@keyframes docs-headless-spin": {
        "to": {"transform": "rotate(360deg)"},
    },
}


@define_component()
async def UiPrimitivesPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/ui_primitives.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template(doc, context.props.path, extra_content=SpinnerShowcase({}))


UiPrimitivesPage.scoped_style = DOCS_PAGE_SCOPED_STYLE
