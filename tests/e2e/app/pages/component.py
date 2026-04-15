from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component
def FunctionStylePage(context: ComponentContext[None]):
    context.set_title("Function Component - E2E")
    msg = "Hello from function component!"

    return html.DIV(
        {"data-testid": "function-style-page"},
        html.H2({}, "Function Style Component"),
        html.P({"data-testid": "function-msg"}, msg),
    )
