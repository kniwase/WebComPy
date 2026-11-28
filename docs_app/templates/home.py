from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.ui.code_block import CodeBlock
from webcompy.utils import strip_multiline_text

from ..components.ui import DocsButton, DocsCard, DocsLink, DocsSection


def _code(code: str) -> str:
    """Pre-process Python triple-quoted string literal so that the leading indentation introduced by the template does not appear in the rendered output. Equivalent to the old SyntaxHighlighting wrapper's ``_strip_code`` helper."""
    return strip_multiline_text(code).strip()


@define_component()
def HomeContent(_: ComponentContext[None]):
    return html.DIV(
        {"class": "page-container home-page"},
        html.SECTION(
            {"class": "hero"},
            html.H1({}, "Build Frontend in Python"),
            html.P(
                {"class": "hero-subtitle"},
                "Python-native reactive components with routing and SSR/SSG — "
                "all in Python, running in the browser via PyScript.",
            ),
            html.DIV(
                {"class": "hero-actions"},
                DocsButton(
                    {
                        "text": "Get Started",
                        "to": "/documents/getting-started/what-is-webcompy",
                        "variant": "primary",
                    }
                ),
                DocsButton(
                    {
                        "text": "View on GitHub",
                        "href": "https://github.com/kniwase/WebComPy",
                    }
                ),
            ),
        ),
        html.SECTION(
            {"class": "feature-cards"},
            DocsCard(
                {"title": "Reactive by default"},
                slots={
                    "default": lambda: (
                        "Signals and computed values keep the DOM in sync automatically — no manual refresh calls."
                    )
                },
            ),
            DocsCard(
                {"title": "Components & Router"},
                slots={
                    "default": lambda: (
                        "Function-style components with props, slots, and scoped CSS, plus client-side routing in history or hash mode."
                    )
                },
            ),
            DocsCard(
                {"title": "CLI, SSR & SSG"},
                slots={
                    "default": lambda: (
                        "Scaffold projects, run a dev server with live reload, and pre-render pages with server-side rendering or static site generation."
                    )
                },
            ),
            DocsCard(
                {"title": "PyScript runtime"},
                slots={
                    "default": lambda: (
                        "Your Python runs in the browser via PyScript — reuse the ecosystem you know, including numpy and friends."
                    )
                },
            ),
            DocsCard(
                {"title": "Coming from Jinja2 + FastAPI?"},
                slots={
                    "default": lambda: html.DIV(
                        {},
                        "Migrate server-rendered FastAPI pages incrementally with ASGI host mounting and live before/after examples. ",
                        DocsLink(
                            {
                                "to": "/documents/migration/from-jinja2-fastapi",
                                "text": "Read the Migration Guide →",
                            }
                        ),
                    )
                },
            ),
            DocsCard(
                {"title": "Accessible UI & Themes"},
                slots={
                    "default": lambda: html.DIV(
                        {},
                        "Headless and token-themed dialogs, forms, and disclosures with built-in light and dark modes. ",
                        DocsLink(
                            {
                                "to": "/documents/basic/ui-primitives",
                                "text": "Explore UI Primitives →",
                            }
                        ),
                    )
                },
            ),
        ),
        DocsSection(
            {"heading": "Try it in a minute"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    "Scaffold a project with the recommended uv setup:",
                    CodeBlock(
                        {
                            "lang": "bash",
                            "code": _code(
                                """
                                mkdir webcompy-project && cd webcompy-project
                                uv init
                                uv add "webcompy @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy"
                                uv add "webcompy-server @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-server"
                                uv add "webcompy-cli @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-cli"
                                uv run python -m webcompy init
                                """
                            ),
                        }
                    ),
                    "Then define your first component:",
                    CodeBlock(
                        {
                            "lang": "python",
                            "code": _code(
                                """
                                from webcompy.components import ComponentContext, define_component
                                from webcompy.elements import html


                                @define_component()
                                def HomePage(context: ComponentContext[None]):
                                    return html.H1({}, "Hello WebComPy!")
                                """
                            ),
                        }
                    ),
                    DocsLink(
                        {
                            "to": "/documents/getting-started/installation",
                            "text": "Full setup → Installation",
                        }
                    ),
                    html.BR(),
                    "Prefer Poetry? See the ",
                    DocsLink(
                        {
                            "to": "/documents/getting-started/installation",
                            "text": "Installation",
                        }
                    ),
                    " guide for the Poetry path.",
                )
            },
        ),
        html.FOOTER(
            {"class": "footer-strip"},
            DocsLink(
                {
                    "href": "https://github.com/kniwase/WebComPy",
                    "text": "Source Code",
                }
            ),
            DocsLink(
                {
                    "href": "https://github.com/kniwase/WebComPy/discussions",
                    "text": "Discussions",
                }
            ),
            html.SPAN(
                {"class": "footer-note"},
                "WebComPy is developed in the open — discussions and pull requests are welcome.",
            ),
        ),
    )


HomeContent.scoped_style = {
    ".page-container": {
        "max-width": "1200px",
        "margin": "0 auto",
        "padding": "var(--space-4)",
    },
    ".hero": {
        "text-align": "center",
        "padding": "var(--space-5) 0",
    },
    ".hero-subtitle": {
        "color": "var(--color-fg)",
        "font-size": "var(--font-size-xl)",
    },
    ".hero-actions": {
        "display": "flex",
        "gap": "var(--space-3)",
        "justify-content": "center",
        "margin-top": "var(--space-4)",
    },
    ".feature-cards": {
        "display": "grid",
        "grid-template-columns": "repeat(3, minmax(0, 1fr))",
        "gap": "var(--space-4)",
        "align-items": "stretch",
    },
    "@media (max-width: 1024px)": {
        ".feature-cards": {
            "grid-template-columns": "repeat(2, minmax(0, 1fr))",
        },
    },
    "@media (max-width: 640px)": {
        ".feature-cards": {
            "grid-template-columns": "minmax(0, 1fr)",
        },
    },
    ".footer-strip": {
        "display": "flex",
        "flex-wrap": "wrap",
        "gap": "var(--space-3)",
        "align-items": "center",
        "justify-content": "center",
        "padding": "var(--space-4) 0",
        "border-top": "1px solid var(--color-border)",
        "margin-top": "var(--space-5)",
    },
    ".footer-note": {
        "color": "var(--color-fg)",
    },
}
