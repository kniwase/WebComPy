from webcompy.elements import html
from webcompy.components import (
    component_class,
    NonPropsComponentBase,
    component_template,
)
from webcompy.router import RouterLink


@component_class
class Navigation(NonPropsComponentBase):
    def __init__(self) -> None:
        pass

    @component_template
    def template(self):
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
