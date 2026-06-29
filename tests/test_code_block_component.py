from __future__ import annotations

from typing import Any

import pytest

from webcompy.di import DIScope
from webcompy.di._scope import _active_di_scope
from webcompy.ports._keys import DOM_PORT_KEY
from webcompy.testing._ports import FakeBrowserDOMPort
from webcompy.ui.code_block._component import CodeBlock
from webcompy.ui.code_block._highlight import highlight
from webcompy.ui.code_block.lexers._registry import (
    register_builtin_lexers,
    reset_lexer_registry,
)


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    reset_lexer_registry()
    register_builtin_lexers()


class _StubContext:
    def __init__(self, props: dict | None = None) -> None:
        self._props = props or {}

    @property
    def props(self) -> dict:
        return self._props

    def slots(self, name: str, fallback: Any = None) -> Any:
        return fallback

    def on_before_rendering(self, func: Any) -> None: ...
    def on_after_rendering(self, func: Any) -> None: ...
    def on_before_destroy(self, func: Any) -> None: ...
    def get_title(self) -> str:
        return ""

    def get_meta(self) -> dict:
        return {}

    def set_title(self, title: str) -> None: ...
    def set_meta(self, key: str, attributes: dict) -> None: ...
    def provide(self, key: object, value: Any) -> None: ...
    def use_reactive_scoped_style(self, style: Any) -> None: ...


def _render(props: dict):
    scope = DIScope()
    scope.provide(DOM_PORT_KEY, FakeBrowserDOMPort())
    token = _active_di_scope.set(scope)
    try:
        return CodeBlock._component_def(_StubContext(props))
    finally:
        _active_di_scope.reset(token)


def _class(el: Any) -> str:
    """Resolve the ``class`` attribute from an Element-like object."""
    raw = el._attrs.get("class") if hasattr(el, "_attrs") else None
    if raw is None:
        return ""
    return str(raw.value) if hasattr(raw, "value") else str(raw)


def test_codeblock_static_path_does_not_create_signal() -> None:
    """Static code string MUST take the early-return path: no Signal/Computed
    wrapping. The returned VDOM tree MUST contain a <pre class=\"code-block\">
    with the highlight() output as its <code> child's inner HTML."""
    code = "x = 1\n"
    expected_inner = highlight(code, "python")
    pre = _render({"code": code, "lang": "python"})
    assert pre._tag_name == "pre"
    assert "code-block" in _class(pre)
    assert len(pre._children) == 1
    code_child = pre._children[0]
    assert code_child._tag_name == "code"
    assert "language-python" in _class(code_child)
    raw = code_child._children[0]
    assert raw._html == expected_inner


def test_codeblock_static_path_explicit_lang() -> None:
    code = "x = 1"
    pre = _render({"code": code, "lang": "python"})
    code_child = pre._children[0]
    assert "language-python" in _class(code_child)
    raw = code_child._children[0]
    assert "x" in raw._html
    assert "1" in raw._html


def test_codeblock_dynamic_signal_path_uses_computed() -> None:
    """A Signal-backed ``code`` prop MUST take the reactive path. The
    inner RawHTML MUST wrap a Computed (not a plain str)."""
    from webcompy.signal import Signal, SignalBase

    sig = Signal("def foo(): pass")
    pre = _render({"code": sig, "lang": "python"})
    raw = pre._children[0]._children[0]
    assert isinstance(raw._html, SignalBase)
    initial_html = raw._html.value
    assert "tok-kw" in initial_html


def test_codeblock_static_branch_keeps_wrapper_stable() -> None:
    """Sanity: the static branch must return a VDOM tree whose root is a
    <pre class=\"code-block\"> with one <code> child (regression guard for
    the early-return change)."""
    pre = _render({"code": "x = 1", "lang": "python"})
    assert pre._tag_name == "pre"
    assert len(pre._children) == 1
    assert pre._children[0]._tag_name == "code"


def test_codeblock_static_branch_html_matches_highlight() -> None:
    """Regression test: the static branch's inner HTML MUST be byte-for-byte
    identical to the result of ``highlight(code, lang)``."""
    code = "def foo():\n    return 42"
    pre = _render({"code": code, "lang": "python"})
    raw = pre._children[0]._children[0]
    assert raw._html == highlight(code, "python")
