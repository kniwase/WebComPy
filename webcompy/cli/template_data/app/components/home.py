from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext


@define_component
def Home(context: ComponentContext[RouterContext]):
    context.set_title("WebCompy Template")
    
    return html.H3(
        {},
        "WebCompy Template",
    )
