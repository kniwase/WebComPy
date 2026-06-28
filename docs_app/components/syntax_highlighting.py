from typing import TypedDict

from webcompy.elements import create_element, raw_html
from webcompy.signal import SignalBase, computed
from webcompy.ui.code_block import highlight
from webcompy.utils import strip_multiline_text


class SyntaxHighlightingProps(TypedDict, total=False):
    code: str | SignalBase[str]
    lang: str


def _resolve_code(code_signal: SignalBase[str]) -> str:
    value = code_signal.value
    if isinstance(value, str):
        return value
    return str(value)


def _strip_code(value: str) -> str:
    if not value:
        return value
    return strip_multiline_text(value).strip()


def _code_block(lang: str, html_body: str):
    return create_element(
        "pre",
        {"class": "code-block"},
        create_element(
            "code",
            {"class": f"language-{lang}"},
            raw_html(html_body),
        ),
    )


def SyntaxHighlighting(props: SyntaxHighlightingProps):
    initial_code = props.get("code", "")
    lang = props.get("lang", "text")

    if isinstance(initial_code, SignalBase):
        code_signal: SignalBase[str] = initial_code
        highlighted = computed(lambda: highlight(_strip_code(_resolve_code(code_signal)), lang))
        return _code_block(lang, highlighted)

    return _code_block(
        lang,
        highlight(_strip_code(str(initial_code)), lang),
    )
