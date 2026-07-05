from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component
def ClassStylePage(context: ComponentContext[None]):
    context.set_title("Class Style - E2E")

    return html.DIV(
        {"data-testid": "class-style-page"},
        html.H2({}, "Class Style Component"),
        html.P({"data-testid": "class-msg"}, "Hello from class component!"),
    )


ClassStylePage.scoped_style = {}
