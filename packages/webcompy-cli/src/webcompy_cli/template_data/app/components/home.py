from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext


@define_component
def Home(context: ComponentContext[RouterContext]):
    context.set_title("WebCompy Template")

    return html.H3(
        {},
        "WebCompy Template",
    )
