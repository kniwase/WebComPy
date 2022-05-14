from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
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
                "WebComPy is Python frontend framework for PyScript, which has following features.",
                html.UL(
                    {},
                    html.LI({}, "Component-based declarative rendering"),
                    html.LI({}, "Automatic DOM refreshing"),
                    html.LI({}, "Built-in router"),
                    html.LI(
                        {},
                        "CLI tools (Project template, Build-in HTTP server, Static Site Generator)",
                    ),
                    html.LI({}, "Type Annotation"),
                ),
            ),
        ),
        html.SECTION(
            {"class": "content"},
            html.H2(
                {"class": "heading"},
                "Get started",
            ),
            html.DIV(
                {"class": "body"},
                "Run following commands to initilize a new project.",
                SyntaxHighlighting(
                    {
                        "lang": "bash",
                        "code": """
                            mkdir webcompy-project
                            cd webcompy-project
                            pip install webcompy
                            python -m webcompy init
                            python -m webcompy start --dev
                        """,
                    }
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
}
