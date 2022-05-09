from typing import TypedDict
from webcompy.elements import html, DomNodeRef
from webcompy.components import define_component, ComponentContext
from webcompy.utils import strip_multiline_text
from webcompy._browser._modules import browser


class SyntaxHighlightingProps(TypedDict):
    code: str
    lang: str


@define_component
def SyntaxHighlighting(context: ComponentContext[SyntaxHighlightingProps]):
    code_ref = DomNodeRef()

    @context.on_after_rendering
    def _():
        if browser:
            browser.window.hljs.highlightElement(code_ref.node)

    return html.PRE(
        {},
        html.CODE(
            {"class": "language-" + context.props["lang"], ":ref": code_ref},
            strip_multiline_text(context.props["code"]).strip(),
        ),
    )


SyntaxHighlighting.scoped_style = {
    "pre code": {
        "font-size": "14px",
        "line-height": "1.2",
        "border-radius": "5px",
    }
}
