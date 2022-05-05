from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext


@define_component
def NotFound(context: ComponentContext[RouterContext]):
    return html.DIV(
        {},
        html.H3(
            {},
            "NotFound",
        ),
        html.PRE(
            {},
            context.props.path,
        ),
    )
