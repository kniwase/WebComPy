"""``CodeBlock`` component rendering syntax-highlighted code as token spans."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element, repeat
from webcompy.signal import SignalBase, use_computed
from webcompy.ui.code_block._highlight import (
    _token_span_classes,
    _tokenize_with_fallback,
)
from webcompy.ui.code_block._tokens import Token


class CodeBlockProps(TypedDict, total=False):
    code: str | SignalBase[str]
    lang: str


def _token_span(token: Token) -> Any:
    return create_element("span", {"class": _token_span_classes(token.type)}, token.value)


@define_component()
def CodeBlock(context: ComponentContext[CodeBlockProps]) -> Any:
    """Render source code with syntax highlighting inside ``pre``/``code``.

    Tokenizes the code with the lexer registered for ``lang`` and renders
    one ``<span>`` per token as a direct child of the ``<code>`` element.
    When the language is unknown or tokenization produces no tokens, the
    whole code is rendered as a single ``tok-ident`` span. Empty code
    renders no token spans. When ``code`` is a ``Signal``, the spans
    re-render from a reactive token list whenever the signal value changes.

    Args:
        context: Component context carrying the ``code`` and ``lang``
            props.

    Returns:
        The rendered element tree: a ``pre.code-block`` wrapping a
        ``code.language-{lang}`` element whose direct children are the
        token spans.

    """
    props = context.props or {}
    initial_code = props.get("code", "")
    lang = props.get("lang", "text")

    if not isinstance(initial_code, SignalBase):
        tokens = _tokenize_with_fallback(_resolve_static(initial_code), lang)
        return create_element(
            "pre",
            {"class": "code-block"},
            create_element(
                "code",
                {"class": f"language-{lang}"},
                *(_token_span(token) for token in tokens),
            ),
        )

    code_signal: SignalBase[str] = initial_code
    tokens = use_computed(lambda: _tokenize_with_fallback(_resolve_code(code_signal), lang))

    return create_element(
        "pre",
        {"class": "code-block"},
        create_element(
            "code",
            {"class": f"language-{lang}"},
            repeat(tokens, _token_span),
        ),
    )


def _resolve_static(code: str | object) -> str:
    if isinstance(code, str):
        return code
    return str(code)


def _resolve_code(code_signal: SignalBase[str]) -> str:
    value = code_signal.value
    if isinstance(value, str):
        return value
    return str(value)
