from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext


@define_component
def HomePage(context: ComponentContext[RouterContext]):
    context.set_title("Home - E2E")
    return html.DIV({"data-testid": "home-page"}, html.H1({}, "E2E Test App"))
