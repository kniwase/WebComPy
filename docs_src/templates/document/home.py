from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext


@define_component
def DocumentHome(_: ComponentContext[RouterContext]):
    return html.DIV({}, "Work In Progress...")
