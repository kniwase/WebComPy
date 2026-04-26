from webcompy.components import ComponentContext, define_component
from webcompy.elements import html

from ..components.syntax_highlighting import SyntaxHighlighting


@define_component
def Home(_: ComponentContext[None]):
    return html.DIV(
        {"class": "container"},
        html.SECTION(
            {"class": "content"},
            html.H2(
                {"class": "heading"},
                "What is WebComPy",
            ),
            html.DIV(
                {"class": "body"},
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
            ),
        ),
        html.SECTION(
            {"class": "content"},
            html.H2(
                {"class": "heading"},
                "Get started with uv (Recommended)",
            ),
            html.DIV(
                {"class": "body"},
                "Create a new project and set up dependencies using ",
                html.STRONG({}, "uv"),
                ".",
                SyntaxHighlighting(
                    {
                        "lang": "bash",
                        "code": """
                            mkdir webcompy-project && cd webcompy-project
                            uv init
                            uv add webcompy
                            uv run python -m webcompy init
                        """,
                    }
                ),
                "Add browser dependencies to ",
                html.CODE({}, "[project.optional-dependencies]"),
                " in ",
                html.CODE({}, "pyproject.toml"),
                ":",
                SyntaxHighlighting(
                    {
                        "lang": "toml",
                        "code": """
                            [project.optional-dependencies]
                            browser = ["numpy", "matplotlib"]
                        """,
                    }
                ),
                "Configure ",
                html.CODE({}, "webcompy_config.py"),
                " to use auto-discovery, and ",
                html.CODE({}, "webcompy_server_config.py"),
                " with ",
                html.CODE({}, "LockfileSyncConfig"),
                ":",
                SyntaxHighlighting(
                    {
                        "lang": "python",
                        "code": """
                            # webcompy_config.py
                            app_config = AppConfig(
                                app_package=Path(__file__).parent / "app",
                                base_url="/",
                                dependencies=None,
                                dependencies_from="browser",
                            )

                            # webcompy_server_config.py
                            lockfile_sync_config = LockfileSyncConfig(sync_group="browser")
                        """,
                    }
                ),
                "Generate the lock file and start the dev server:",
                SyntaxHighlighting(
                    {
                        "lang": "bash",
                        "code": """
                            uv run python -m webcompy lock
                            uv run python -m webcompy start --dev
                        """,
                    }
                ),
            ),
        ),
        html.SECTION(
            {"class": "content"},
            html.H2(
                {"class": "heading"},
                "Get started with Poetry",
            ),
            html.DIV(
                {"class": "body"},
                "If you prefer ",
                html.STRONG({}, "Poetry"),
                ", use the following setup:",
                SyntaxHighlighting(
                    {
                        "lang": "bash",
                        "code": """
                            mkdir webcompy-project && cd webcompy-project
                            poetry new webcompy-project && cd webcompy-project
                            poetry add webcompy
                            poetry run python -m webcompy init
                        """,
                    }
                ),
                "Add browser dependencies to ",
                html.CODE({}, "[project.optional-dependencies]"),
                " in ",
                html.CODE({}, "pyproject.toml"),
                " (same as the uv setup above).",
                html.BR(),
                "Then configure ",
                html.CODE({}, "webcompy_config.py"),
                " and ",
                html.CODE({}, "webcompy_server_config.py"),
                " as shown above, and run:",
                SyntaxHighlighting(
                    {
                        "lang": "bash",
                        "code": """
                            poetry run python -m webcompy lock
                            poetry run python -m webcompy start --dev
                        """,
                    }
                ),
                html.EM(
                    {},
                    "Note: ",
                    html.CODE({}, "webcompy lock --install"),
                    " uses ",
                    html.CODE({}, "uv pip"),
                    " or ",
                    html.CODE({}, "pip"),
                    ", not ",
                    html.CODE({}, "poetry install"),
                    ". Use ",
                    html.CODE({}, "webcompy lock --sync"),
                    " to compare versions with ",
                    html.CODE({}, "pyproject.toml"),
                    ".",
                ),
            ),
        ),
        html.SECTION(
            {"class": "content"},
            html.H2(
                {"class": "heading"},
                "Lock File Commands",
            ),
            html.DIV(
                {"class": "body"},
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
                            html.TD({}, html.CODE({}, "webcompy lock")),
                            html.TD({}, "Generate or update the lock file"),
                        ),
                        html.TR(
                            {},
                            html.TD({}, html.CODE({}, "webcompy lock --export")),
                            html.TD({}, "Export lock file dependencies to requirements.txt"),
                        ),
                        html.TR(
                            {},
                            html.TD({}, html.CODE({}, "webcompy lock --sync")),
                            html.TD({}, "Compare lock file with pyproject.toml / requirements.txt"),
                        ),
                        html.TR(
                            {},
                            html.TD({}, html.CODE({}, "webcompy lock --install")),
                            html.TD({}, "Export and install lock file dependencies"),
                        ),
                    ),
                ),
            ),
        ),
        html.SECTION(
            {"class": "content"},
            html.H2(
                {"class": "heading"},
                "Source Code",
            ),
            html.DIV(
                {"class": "body"},
                html.A(
                    {"href": "https://github.com/kniwase/WebComPy"},
                    "Project Home",
                ),
            ),
        ),
    )


Home.scoped_style = {
    ".container": {
        "margin": "2px auto",
        "padding": "5px 5px",
    },
    ".container .content": {
        "margin": "10px auto",
        "padding": "10px",
        "background-color": "#fafafa",
        "border-radius": "15px",
    },
    ".container .content .body": {
        "margin": "10px auto",
    },
    ".container .content .heading": {
        "padding": "5px",
        "border-bottom": "double 3px black",
        "font-size": "20px",
    },
    ".commands-table": {
        "width": "100%",
        "border-collapse": "collapse",
        "margin-top": "10px",
    },
    ".commands-table th, .commands-table td": {
        "padding": "8px 12px",
        "text-align": "left",
        "border-bottom": "1px solid #ddd",
    },
    ".commands-table th": {
        "background-color": "#f0f0f0",
        "font-weight": "bold",
    },
}
