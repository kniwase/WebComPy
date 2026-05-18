from typing import TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.di import inject
from webcompy.elements import DomNodeRef, html
from webcompy.ports._keys import HOST_PORT_KEY
from webcompy.utils import strip_multiline_text


class SyntaxHighlightingProps(TypedDict):
    code: str
    lang: str


@define_component
def SyntaxHighlighting(context: ComponentContext[SyntaxHighlightingProps]):
    code_ref = DomNodeRef()
    get_hljs = inject(HOST_PORT_KEY).create_js_global_getter("hljs")

    @context.on_after_rendering
    def _():
        hljs = get_hljs()
        if hljs is not None:
            hljs.highlightElement(code_ref.element)

    return html.PRE(
        {},
        html.CODE(
            {"class": f"language-{context.props['lang']}", ":ref": code_ref},
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
