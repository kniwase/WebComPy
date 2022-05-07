from webcompy.elements import html
from webcompy.components import ComponentContext, define_component
from webcompy.router import RouterView
from .navigation import Navigation


@define_component
def Root(_: ComponentContext[None]):
    return html.DIV(
        {},
        Navigation(None),
        RouterView(),
    )
