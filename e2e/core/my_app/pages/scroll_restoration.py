from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext, RouterLink


@define_component
def ScrollLongPage(context: ComponentContext[RouterContext]):
    context.set_title("Scroll Long - E2E")
    return html.DIV(
        {"data-testid": "scroll-long-page"},
        html.H2({}, "Scroll Restoration Long Page"),
        html.DIV({"style": "height: 3000px;"}, html.P({}, "Tall content")),
        RouterLink(
            to="/scroll-target",
            text=["Go to target"],
            attrs={"data-testid": "scroll-nav-target"},
        ),
    )


@define_component
def ScrollTargetPage(context: ComponentContext[RouterContext]):
    context.set_title("Scroll Target - E2E")
    return html.DIV(
        {"data-testid": "scroll-target-page"},
        html.H2({}, "Scroll Restoration Target Page"),
    )
