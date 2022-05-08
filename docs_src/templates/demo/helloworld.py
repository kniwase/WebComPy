from webcompy.elements import html
from webcompy.components import define_component, ComponentContext


@define_component
def HelloWorld(_: ComponentContext[None]):
    return html.DIV(
        {},
        html.H1(
            {},
            "Hello WebComPy!",
        ),
    )
