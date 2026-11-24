from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext, RouterLink

from ...components.ui import DocsCard
from ...docs_manifest import DOCS_SECTIONS


@define_component()
def DocumentHomePage(context: ComponentContext[RouterContext]):
    context.set_title("Documents - WebComPy Docs")

    has_server_tooling = any(section["title"] == "Server & Tooling" for section in DOCS_SECTIONS)
    cheat_sheet = (
        (
            DocsCard(
                {"title": "Operators' cheat sheet"},
                slots={
                    "default": lambda: html.DIV(
                        {"class": "docs-cheat-sheet"},
                        html.P(
                            {},
                            "Quick operational entry points for building, configuring, embedding, and testing apps:",
                        ),
                        html.UL(
                            {"class": "docs-cheat-sheet-list"},
                            html.LI(
                                {},
                                RouterLink(to="/documents/server/cli-reference", text=["CLI Reference"]),
                                " — subcommands, flags, and headless browser inspection",
                            ),
                            html.LI(
                                {},
                                RouterLink(
                                    to="/documents/server/project-configuration", text=["Project Configuration"]
                                ),
                                " — pyproject.toml dependencies, webcompy_config.py, resources, and lockfile",
                            ),
                            html.LI(
                                {},
                                RouterLink(to="/documents/server/asgi-integration", text=["ASGI Integration"]),
                                " — embedding in FastAPI/Starlette and mounting sub-apps",
                            ),
                            html.LI(
                                {},
                                RouterLink(to="/documents/server/serving-modes", text=["Serving Modes"]),
                                " — CDN vs local runtime/wasm, wheel bundling, and offline deploys",
                            ),
                            html.LI(
                                {},
                                RouterLink(to="/documents/server/testing", text=["Testing"]),
                                " — TestRenderer, fake ports, ASGI helpers, and tier policy",
                            ),
                        ),
                    )
                },
            ),
        )
        if has_server_tooling
        else ()
    )

    return html.DIV(
        {"class": "docs-index"},
        html.H1({}, "Documentation"),
        html.P({"class": "docs-index-intro"}, "Guides for installing WebComPy and building your first app."),
        *cheat_sheet,
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
    " .docs-cheat-sheet-list": {
        "margin": "var(--space-2) 0 0 0",
        "padding-left": "var(--space-5)",
        "line-height": "1.6",
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
