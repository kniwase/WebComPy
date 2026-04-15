from webcompy.components import (
    TypedComponentBase,
    component_class,
    component_template,
)
from webcompy.elements import html


@component_class
class ScopedStylePage(TypedComponentBase(props_type=None)):
    @component_template
    def template(self):
        return html.DIV(
            {"data-testid": "scoped-style-page"},
            html.H2({}, "Scoped Style Tests"),
            html.P({"data-testid": "styled-text", "class": "styled-text"}, "Styled text"),
        )


ScopedStylePage.scoped_style = {
    ".styled-text": {
        "color": "red",
        "font-weight": "bold",
    },
}
