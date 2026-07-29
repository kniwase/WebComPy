from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext

from ...templates.document.limitations import DocumentLimitations


@define_component
def LimitationsPage(context: ComponentContext[RouterContext]):
    context.set_title("Limitations - WebComPy")
    return html.DIV({}, DocumentLimitations(None))
