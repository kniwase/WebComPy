from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component
def HelloWorld(_: ComponentContext[None]):
    return html.DIV(
        {},
        html.H1(
            {},
            "Hello WebComPy!",
        ),
    )
