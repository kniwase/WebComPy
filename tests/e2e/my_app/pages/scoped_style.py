from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component
def ScopedStylePage(context: ComponentContext[None]):
    context.set_title("Scoped Style - E2E")

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
