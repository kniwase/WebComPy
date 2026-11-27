"""``CodeBlock`` component rendering syntax-highlighted code as token spans."""

from __future__ import annotations

import asyncio
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.components._hooks import _register_before_destroy_chained
from webcompy.di import inject
from webcompy.elements import create_element, repeat
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, HOST_PORT_KEY
from webcompy.signal import Signal, SignalBase, use_computed
from webcompy.ui.code_block._highlight import (
    _token_span_classes,
    _tokenize_with_fallback,
)
from webcompy.ui.code_block._tokens import Token


class CodeBlockProps(TypedDict, total=False):
    code: str | SignalBase[str]
    lang: str
    copyable: bool


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
    When ``copyable`` is ``True``, the block is wrapped in a container
    with a copy-to-clipboard button alongside the ``<pre>`` element.

    Args:
        context: Component context carrying the ``code``, ``lang``, and
            optional ``copyable`` props.

    Returns:
        The rendered element tree: a ``pre.code-block`` wrapping a
        ``code.language-{lang}`` element whose direct children are the
        token spans, or a ``div.code-block-container`` containing a copy
        button and ``pre.code-block`` when ``copyable`` is ``True``.

    """
    props = context.props or {}
    initial_code = props.get("code", "")
    lang = props.get("lang", "text")
    copyable = bool(props.get("copyable", False))

    if not isinstance(initial_code, SignalBase):
        tokens = _tokenize_with_fallback(_resolve_static(initial_code), lang)
        pre_el = create_element(
            "pre",
            {"class": "code-block"},
            create_element(
                "code",
                {"class": f"language-{lang}"},
                *(_token_span(token) for token in tokens),
            ),
        )
    else:
        code_signal: SignalBase[str] = initial_code
        tokens = use_computed(lambda: _tokenize_with_fallback(_resolve_code(code_signal), lang))
        pre_el = create_element(
            "pre",
            {"class": "code-block"},
            create_element(
                "code",
                {"class": f"language-{lang}"},
                repeat(tokens, _token_span),
            ),
        )

    if not copyable:
        return pre_el

    copied: Signal[bool] = Signal(False)
    destroyed = [False]
    reset_gen = [0]

    def _on_destroy() -> None:
        destroyed[0] = True

    _register_before_destroy_chained(_on_destroy)

    async def _finalize(promise: Any, gen: int) -> None:
        if promise is not None and hasattr(promise, "__await__"):
            try:
                await promise
            except Exception:
                if not destroyed[0] and reset_gen[0] == gen:
                    copied.value = False
                return
        await asyncio.sleep(1.5)
        if not destroyed[0] and reset_gen[0] == gen:
            copied.value = False

    def _on_copy(_ev: Any) -> None:
        code_text = (
            _resolve_code(initial_code) if isinstance(initial_code, SignalBase) else _resolve_static(initial_code)
        )
        host = inject(HOST_PORT_KEY, default=None)
        if host is None:
            return
        nav = host.create_js_global_getter("navigator")()
        clipboard = getattr(nav, "clipboard", None)
        write_text = getattr(clipboard, "writeText", None)
        if not callable(write_text):
            return
        try:
            promise = write_text(code_text)
        except Exception:
            return
        copied.value = True
        reset_gen[0] += 1
        gen = reset_gen[0]
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY, default=None)
        if scheduler is not None:
            scheduler.schedule(_finalize(promise, gen), render=False)

    copy_btn = create_element(
        "button",
        {
            "type": "button",
            "class": "code-block-copy",
            "aria-label": use_computed(lambda: "Copied to clipboard" if copied.value else "Copy code"),
            "data-copied": use_computed(lambda: "true" if copied.value else "false"),
            "@click": _on_copy,
        },
        use_computed(lambda: "Copied" if copied.value else "Copy"),
    )
    return create_element("div", {"class": "code-block-container"}, copy_btn, pre_el)


def _resolve_static(code: str | object) -> str:
    if isinstance(code, str):
        return code
    return str(code)


def _resolve_code(code_signal: SignalBase[str]) -> str:
    value = code_signal.value
    if isinstance(value, str):
        return value
    return str(value)
