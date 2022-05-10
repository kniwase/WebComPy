from webcompy.elements import html
from webcompy.components import define_component, ComponentContext


@define_component
def DocumentHome(_: ComponentContext[None]):
    return html.DIV({}, "Work In Progress...")
