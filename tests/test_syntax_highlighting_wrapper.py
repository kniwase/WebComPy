from __future__ import annotations

import sys
from pathlib import Path

import pytest

from webcompy.components._component import HeadPropsStore
from webcompy.di import DIScope
from webcompy.di._keys import _HEAD_PROPS_KEY
from webcompy.di._scope import _active_di_scope
from webcompy.signal import Signal
from webcompy.ui.code_block.lexers._registry import (
    register_builtin_lexers,
    reset_lexer_registry,
)

DOCS_APP_DIR = Path(__file__).parent.parent / "docs_app"


@pytest.fixture(autouse=True)
def _add_docs_app_path(monkeypatch):
    monkeypatch.setattr(sys, "path", [str(DOCS_APP_DIR), *sys.path])


@pytest.fixture(autouse=True)
def _ensure_lexers() -> None:
    reset_lexer_registry()
    register_builtin_lexers()


@pytest.fixture
def di_scope():
    scope = DIScope()
    scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
    token = _active_di_scope.set(scope)
    try:
        yield scope
    finally:
        _active_di_scope.reset(token)


def _syntax_highlighting_render(props: dict):
    from docs_app.components.syntax_highlighting import SyntaxHighlighting

    return SyntaxHighlighting._component_def(_StubContext(props))


class _StubContext:
    def __init__(self, props: dict | None = None) -> None:
        self._props = props or {}

    @property
    def props(self) -> dict:
        return self._props

    def slots(self, name: str, fallback: object = None) -> object:
        return fallback

    def on_before_rendering(self, func: object) -> None: ...
    def on_after_rendering(self, func: object) -> None: ...
    def on_before_destroy(self, func: object) -> None: ...
    def get_title(self) -> str:
        return ""

    def get_meta(self) -> dict:
        return {}

    def set_title(self, title: str) -> None: ...
    def set_meta(self, key: str, attributes: dict) -> None: ...
    def provide(self, key: object, value: object) -> None: ...
    def use_reactive_scoped_style(self, style: object) -> None: ...
    def remove_reactive_scoped_style(self, style: object) -> None: ...


def _highlighted_bash(code: str) -> str:
    from webcompy.ui.code_block._highlight import highlight

    return highlight(code, "bash")


def test_syntax_highlighting_strips_indentation_before_delegating(di_scope) -> None:
    """Regression test for PR #178 sixth-round review: SyntaxHighlighting
    MUST pre-process string ``code`` with ``strip_multiline_text().strip()``
    to remove the leading indentation that comes from Python triple-quoted
    string literals, then delegate to CodeBlock.

    The highlighted inner HTML of the delegated CodeBlock MUST be
    byte-for-byte identical to what ``highlight(stripped, lang)`` would
    produce."""
    code = """
        mkdir webcompy-project && cd webcompy-project
        uv init
        uv add webcompy
    """
    from webcompy.utils import strip_multiline_text

    stripped = strip_multiline_text(code).strip()

    actual = _syntax_highlighting_render({"code": code, "lang": "bash"})

    assert actual._tag_name == "pre"
    code_child = actual._children[0]
    assert code_child._tag_name == "code"
    assert "language-bash" in code_child._attrs["class"]
    html = code_child._children[0]._html
    assert html == _highlighted_bash(stripped)
    assert "mkdir" in html
    assert "webcompy" in html
    assert "uv" in html
    assert "add" in html


def test_syntax_highlighting_passes_through_signal_code(di_scope) -> None:
    """SyntaxHighlighting MUST pass Signal-based code props through to
    CodeBlock unchanged (only string code is pre-processed)."""
    sig = Signal("def foo(): pass")

    actual = _syntax_highlighting_render({"code": sig, "lang": "python"})

    assert actual._tag_name == "pre"
    code_child = actual._children[0]
    assert "language-python" in code_child._attrs["class"]
    actual_html = code_child._children[0]._html.value
    assert "tok-kw" in actual_html
    assert "def" in actual_html


def test_syntax_highlighting_default_lang_is_text(di_scope) -> None:
    """The default ``lang`` value for SyntaxHighlighting MUST be ``"text"``
    so a missing prop falls through to CodeBlock's graceful raw-text
    fallback (since the framework does not register a ``text`` lexer)."""
    actual = _syntax_highlighting_render({"code": "raw text"})

    assert actual._tag_name == "pre"
    code_child = actual._children[0]
    assert "language-text" in code_child._attrs["class"]
    assert "raw text" in code_child._children[0]._html
