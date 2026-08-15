from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext, RouterLink

from ...components.ui import DocsCard
from ...docs_manifest import DOCS_SECTIONS


@define_component("document-home-page")
def DocumentHomePage(context: ComponentContext[RouterContext]):
    context.set_title("Documents - WebComPy Docs")

    return html.DIV(
        {"class": "docs-index"},
        html.H1({}, "Documentation"),
        html.P({"class": "docs-index-intro"}, "Guides for installing WebComPy and building your first app."),
        *tuple(
            html.SECTION(
                {"class": "docs-index-section"},
                html.H2({}, section["title"]),
                html.DIV(
                    {"class": "docs-index-cards"},
                    *tuple(
                        DocsCard(
                            {"title": page["label"]},
                            slots={
                                "default": lambda page=page: RouterLink(to=page["path"], text=["Open " + page["label"]])
                            },
                        )
                        for page in section["pages"]
                    ),
                ),
            )
            for section in DOCS_SECTIONS
        ),
    )


DocumentHomePage.scoped_style = {
    " .docs-index": {
        "max-width": "1200px",
    },
    " .docs-index-intro": {
        "color": "var(--color-fg-muted)",
    },
    " .docs-index-section": {
        "margin-top": "var(--space-5)",
    },
    " .docs-index-cards": {
        "display": "grid",
        "grid-template-columns": "repeat(auto-fill, minmax(14rem, 1fr))",
        "gap": "var(--space-4)",
        "margin-top": "var(--space-3)",
    },
}
