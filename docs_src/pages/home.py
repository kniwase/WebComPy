from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ..templates.home import Home


@define_component
def HomePage(_: ComponentContext[RouterContext]):
    return html.DIV({}, Home(None))
