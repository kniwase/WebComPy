from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.ui.code_block import CodeBlock
from webcompy.utils import strip_multiline_text

from ..components.ui import InlineCode, Section


def _code(code: str) -> str:
    """Pre-process Python triple-quoted string literal so that the leading
    indentation introduced by the template does not appear in the rendered
    output. Equivalent to the old SyntaxHighlighting wrapper's
    ``_strip_code`` helper."""
    return strip_multiline_text(code).strip()


@define_component
def Home(_: ComponentContext[None]):
    return html.DIV(
        {"class": "page-container"},
        Section(
            {"heading": "What is WebComPy"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    "WebComPy is a Python frontend framework for PyScript with the following features.",
                    html.UL(
                        {},
                        html.LI({}, "Component-based declarative rendering"),
                        html.LI({}, "Automatic DOM refreshing"),
                        html.LI({}, "Built-in router"),
                        html.LI(
                            {},
                            "CLI tools (Project scaffolding, Dev server, Static Site Generator)",
                        ),
                        html.LI({}, "Dependency management with lock file sync"),
                    ),
                )
            },
        ),
        Section(
            {"heading": "Get started with uv (Recommended)"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    "Create a new project and set up dependencies using ",
                    html.STRONG({}, "uv"),
                    ".",
                    CodeBlock(
                        {
                            "lang": "bash",
                            "code": _code(
                                """
                                mkdir webcompy-project && cd webcompy-project
                                uv init
                                uv add webcompy
                                uv run python -m webcompy init
                                """
                            ),
                        }
                    ),
                    "Add browser dependencies to ",
                    InlineCode({"text": "[project.optional-dependencies]"}),
                    " in ",
                    InlineCode({"text": "pyproject.toml"}),
                    ":",
                    CodeBlock(
                        {
                            "lang": "toml",
                            "code": _code(
                                """
                                [project.optional-dependencies]
                                browser = ["numpy", "matplotlib"]
                                """
                            ),
                        }
                    ),
                    "Configure ",
                    InlineCode({"text": "webcompy_config.py"}),
                    " with ",
                    InlineCode({"text": "LockfileSyncConfig"}),
                    ":",
                    CodeBlock(
                        {
                            "lang": "python",
                            "code": _code(
                                """
                            # webcompy_config.py
                            import app.app as app_module
                            from webcompy.cli.config import WebComPyBuildConfig, LockfileSyncConfig

                            config = WebComPyBuildConfig(
                                app_module,
                                dependencies=None,
                                dependencies_from="browser",
                                lockfile_sync_config=LockfileSyncConfig(sync_group="browser"),
                            )
                            """
                            ),
                        }
                    ),
                    "Generate the lock file and start the dev server:",
                    CodeBlock(
                        {
                            "lang": "bash",
                            "code": _code(
                                """
                                uv run python -m webcompy lock
                                uv run python -m webcompy start --dev
                                """
                            ),
                        }
                    ),
                )
            },
        ),
        Section(
            {"heading": "Get started with Poetry"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    "If you prefer ",
                    html.STRONG({}, "Poetry"),
                    ", use the following setup:",
                    CodeBlock(
                        {
                            "lang": "bash",
                            "code": _code(
                                """
                                mkdir webcompy-project && cd webcompy-project
                                poetry new webcompy-project && cd webcompy-project
                                poetry add webcompy
                                poetry run python -m webcompy init
                                """
                            ),
                        }
                    ),
                    "Add browser dependencies to ",
                    InlineCode({"text": "[project.optional-dependencies]"}),
                    " in ",
                    InlineCode({"text": "pyproject.toml"}),
                    " (same as the uv setup above).",
                    html.BR(),
                    "Then configure ",
                    InlineCode({"text": "webcompy_config.py"}),
                    " as shown above, and run:",
                    CodeBlock(
                        {
                            "lang": "bash",
                            "code": _code(
                                """
                                poetry run python -m webcompy lock
                                poetry run python -m webcompy start --dev
                                """
                            ),
                        }
                    ),
                    html.EM(
                        {},
                        "Note: ",
                        InlineCode({"text": "webcompy lock --install"}),
                        " uses ",
                        InlineCode({"text": "uv pip"}),
                        " or ",
                        InlineCode({"text": "pip"}),
                        ", not ",
                        InlineCode({"text": "poetry install"}),
                        ". Use ",
                        InlineCode({"text": "webcompy lock --sync"}),
                        " to compare versions with ",
                        InlineCode({"text": "pyproject.toml"}),
                        ".",
                    ),
                )
            },
        ),
        Section(
            {"heading": "Lock File Commands"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    html.TABLE(
                        {"class": "commands-table"},
                        html.THEAD(
                            {},
                            html.TR(
                                {},
                                html.TH({}, "Command"),
                                html.TH({}, "Description"),
                            ),
                        ),
                        html.TBODY(
                            {},
                            html.TR(
                                {},
                                html.TD({}, InlineCode({"text": "webcompy lock"})),
                                html.TD({}, "Generate or update the lock file"),
                            ),
                            html.TR(
                                {},
                                html.TD({}, InlineCode({"text": "webcompy lock --export"})),
                                html.TD({}, "Export lock file dependencies to requirements.txt"),
                            ),
                            html.TR(
                                {},
                                html.TD({}, InlineCode({"text": "webcompy lock --sync"})),
                                html.TD({}, "Compare lock file with pyproject.toml / requirements.txt"),
                            ),
                            html.TR(
                                {},
                                html.TD({}, InlineCode({"text": "webcompy lock --install"})),
                                html.TD({}, "Export and install lock file dependencies"),
                            ),
                        ),
                    ),
                )
            },
        ),
        Section(
            {"heading": "Source Code"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    html.A(
                        {
                            "href": "https://github.com/kniwase/WebComPy",
                            "class": "ui-link",
                        },
                        "Project Home",
                    ),
                )
            },
        ),
    )


Home.scoped_style = {
    ".page-container": {
        "max-width": "1200px",
        "margin": "0 auto",
        "padding": "var(--space-4)",
    },
    ".commands-table": {
        "width": "100%",
        "border-collapse": "collapse",
        "margin-top": "var(--space-3)",
    },
    ".commands-table th, .commands-table td": {
        "padding": "var(--space-2) var(--space-3)",
        "text-align": "left",
        "border-bottom": "1px solid var(--color-border)",
        "color": "var(--color-fg)",
    },
    ".commands-table th": {
        "background-color": "var(--color-bg-elevated)",
        "font-weight": "600",
    },
}
