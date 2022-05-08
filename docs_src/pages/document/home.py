from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ...templates.document.home import DocumentHome


@define_component
def DocumentHomePage(_: ComponentContext[RouterContext]):
    return html.DIV({}, DocumentHome(None))
