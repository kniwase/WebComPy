from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component
def ScopedStylePage(context: ComponentContext[None]):
    context.set_title("Scoped Style - E2E")

    return html.DIV(
        {"data-testid": "scoped-style-page"},
        html.H2({}, "Scoped Style Tests"),
        html.P({"data-testid": "styled-text", "class": "styled-text"}, "Styled text"),
        html.P({"data-testid": "media-text", "class": "media-text"}, "Media query text"),
        html.P({"data-testid": "hover-text", "class": "hover-text"}, "Hover text"),
        html.P({"data-testid": "deep-text", "class": "deep-text"}, "Deep nested text"),
        html.P({"data-testid": "combinator-text", "class": "combinator-text"}, "Combinator text"),
    )


ScopedStylePage.scoped_style = {
    ".styled-text": {
        "color": "red",
        "font-weight": "bold",
    },
    ".media-text": {
        "color": "blue",
        "@media (max-width: 768px)": {
            "color": "green",
        },
    },
    ".hover-text": {
        "color": "purple",
        ":hover": {
            "background-color": "yellow",
        },
    },
    ".deep-text": {
        "color": "orange",
        "@media (max-width: 768px)": {
            "color": "cyan",
            ":hover": {
                "background-color": "pink",
            },
        },
    },
    ".combinator-text": {
        "color": "navy",
        "> span": {
            "font-weight": "bold",
        },
    },
}
