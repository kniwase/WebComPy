from typing import TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.di import inject
from webcompy.elements import DomNodeRef, html
from webcompy.ports._keys import HOST_PORT_KEY
from webcompy.signal import SignalBase
from webcompy.utils import strip_multiline_text

_MAX_CODE_LENGTH = 100_000


class SyntaxHighlightingProps(TypedDict):
    code: str | SignalBase[str]
    lang: str


def _validate_code(text: str) -> str:
    if not isinstance(text, str):
        return ""
    if not text.strip():
        return text
    if len(text) > _MAX_CODE_LENGTH:
        return "[Error: code too large]"
    if "\x00" in text:
        return "[Error: invalid characters]"
    return text


@define_component
def SyntaxHighlighting(context: ComponentContext[SyntaxHighlightingProps]):
    code = context.props["code"]
    code_ref = DomNodeRef()
    get_hljs = inject(HOST_PORT_KEY).create_js_global_getter("hljs")

    def run_highlight():
        source = code.value if isinstance(code, SignalBase) else code
        source = _validate_code(source)
        if not source.strip():
            return
        if source.startswith("[Error:"):
            if code_ref.element:
                code_ref.element.textContent = source
            return
        hljs = get_hljs()
        if hljs is not None and code_ref.element:
            stripped = strip_multiline_text(source).strip()
            result = hljs.highlight(stripped, {"language": context.props["lang"]})
            code_ref.element.innerHTML = result.value

    if isinstance(code, SignalBase):
        code.on_after_updating(lambda _: run_highlight())

    @context.on_after_rendering
    def _():
        run_highlight()

    return html.PRE(
        {},
        html.CODE(
            {
                "class": f"language-{context.props['lang']}",
                ":ref": code_ref,
                ":preserve_children": True,
            },
        ),
    )


SyntaxHighlighting.scoped_style = {
    "pre code": {
        "font-size": "14px",
        "line-height": "1.2",
        "border-radius": "5px",
    }
}
