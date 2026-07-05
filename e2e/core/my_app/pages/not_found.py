from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext


@define_component
def NotFound(context: ComponentContext[RouterContext]):
    context.set_title("Not Found - E2E")
    return html.DIV(
        {"data-testid": "not-found"},
        html.H3({}, "Not Found"),
        html.PRE({"data-testid": "not-found-path"}, context.props.path),
    )
