from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterLink


@define_component
def Navigation(context: ComponentContext[None]):
    return html.NAV(
        {},
        html.UL(
            {},
            html.LI(
                {},
                RouterLink(
                    to="/",
                    text=["Home"],
                ),
            ),
            html.LI(
                {},
                RouterLink(
                    to="/fizzbuzz",
                    text=["FizzBuzz"],
                ),
            ),
            html.LI(
                {},
                RouterLink(
                    to="/input",
                    text=["Text Input Sample"],
                ),
            ),
        ),
    )
