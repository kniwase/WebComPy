from typing import TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.signal import SignalBase
from webcompy.ui.code_block import CodeBlock
from webcompy.utils import strip_multiline_text


class SyntaxHighlightingProps(TypedDict, total=False):
    code: str | SignalBase[str]
    lang: str


def _strip_code(value: str) -> str:
    if not value:
        return value
    return strip_multiline_text(value).strip()


@define_component
def SyntaxHighlighting(context: ComponentContext[SyntaxHighlightingProps]):
    """Thin wrapper around ``CodeBlock`` that pre-processes the ``code``
    prop with ``strip_multiline_text().strip()`` so the docs-app template
    literal can be written with its natural indentation. All actual
    rendering logic lives in ``CodeBlock`` to avoid drift between the
    two implementations.

    See ``webcompy/ui/code_block/_component.py`` for the canonical
    component.
    """
    props = context.props or {}
    initial_code = props.get("code", "")
    lang = props.get("lang", "text")

    if isinstance(initial_code, str):
        return CodeBlock({"code": _strip_code(initial_code), "lang": lang})
    return CodeBlock({"code": initial_code, "lang": lang})
