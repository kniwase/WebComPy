from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element, raw_html
from webcompy.signal import Signal, SignalBase, computed
from webcompy.ui.code_block._highlight import highlight


class CodeBlockProps(TypedDict, total=False):
    code: str | SignalBase[str]
    lang: str


@define_component
def CodeBlock(context: ComponentContext[CodeBlockProps]) -> Any:
    props = context.props or {}
    initial_code = props.get("code", "")
    lang = props.get("lang", "text")

    if isinstance(initial_code, SignalBase):
        code_signal: SignalBase[str] = initial_code
    else:
        code_signal = Signal(str(initial_code))

    highlighted = computed(lambda: highlight(_resolve_code(code_signal), lang))

    return create_element(
        "pre",
        {"class": "code-block"},
        create_element(
            "code",
            {"class": f"language-{lang}"},
            raw_html(highlighted),
        ),
    )


def _resolve_code(code_signal: SignalBase[str]) -> str:
    value = code_signal.value
    if isinstance(value, str):
        return value
    return str(value)
