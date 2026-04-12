from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext

from ..templates.home import Home


@define_component
def HomePage(context: ComponentContext[RouterContext]):
    return html.DIV({}, Home(None))
