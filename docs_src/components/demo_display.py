from typing import TypedDict
from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from .syntax_highlighting import SyntaxHighlighting


class DemoComponentProps(TypedDict):
    title: str
    code: str


@define_component
def DemoDisplay(context: ComponentContext[DemoComponentProps]):
    return html.DIV(
        {},
        html.DIV(
            {"class": "card"},
            html.DIV(
                {"class": "card-body"},
                html.H5({"class": "card-title"}, context.props["title"]),
                html.DIV(
                    {"class": "card"},
                    html.DIV(
                        {"class": "card-body"},
                        context.slots("component"),
                    ),
                ),
                html.BR(),
                html.DIV(
                    {"class": "card"},
                    html.DIV({"class": "card-header"}, "Code"),
                    html.DIV(
                        {"class": "card-body"},
                        SyntaxHighlighting(
                            {
                                "lang": "python",
                                "code": context.props["code"],
                            }
                        ),
                    ),
                ),
            ),
        ),
    )
