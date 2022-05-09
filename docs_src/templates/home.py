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
                "WebComPy is Python frontend framework on Browser, which has following features.",
                html.UL(
                    {},
                    html.LI({}, "Component-based declarative rendering"),
                    html.LI({}, "Automatic DOM refreshing"),
                    html.LI({}, "Built-in router"),
                    html.LI({}, "Built-in server / Static Site Generation"),
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
                        """
                    }
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


# What is WebComPy
#

# Component-based declarative rendering
# Automatic DOM refreshing
# Built-in router
# Built-in server / Static Site Generation
# Get started
# mkdir webcompy-project
# cd webcompy-project
# pip install webcompy
# python -m webcompy init
# python -m webcompy start --dev
# then access http://127.0.0.1:8080/WebComPy/
