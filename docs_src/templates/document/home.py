from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component
def DocumentHome(_: ComponentContext[None]):
    return html.DIV({}, "Work In Progress...")
