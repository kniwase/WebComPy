from __future__ import annotations

import html as html_module
import re
from typing import Any

import pytest

from webcompy.components import define_component
from webcompy.di import DIScope
from webcompy.di._scope import _active_di_scope
from webcompy.elements import create_element
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._text import TextElement
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, DOM_PORT_KEY, HOST_PORT_KEY
from webcompy.signal import Computed, Signal, SignalBase, use_state
from webcompy.ui.code_block._component import CodeBlock
from webcompy.ui.code_block._highlight import highlight
from webcompy.ui.code_block._tokens import TokenType
from webcompy.ui.code_block.lexers._registry import (
    register_builtin_lexers,
    register_lexer,
    reset_lexer_registry,
)
from webcompy_server.ports._virtual_dom import VirtualDOMEvent
from webcompy_testing import TestRenderer, run_sync
from webcompy_testing._ports import FakeBrowserDOMPort, FakeBrowserHostPort

_SPAN_RE = re.compile(r'<span class="([^"]+)">(.*?)</span>', re.DOTALL)


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


def _code_element(pre: Any) -> Any:
    assert pre._tag_name == "pre"
    assert "code-block" in _class(pre)
    assert len(pre._children) == 1
    code_el = pre._children[0]
    assert code_el._tag_name == "code"
    return code_el


def test_codeblock_static_path_does_not_create_signal() -> None:
    """Static code string MUST take the early-return path: no Signal/Computed
    wrapping. The returned VDOM tree MUST contain a <pre class=\"code-block\">
    with the token spans as the <code> child's direct children."""
    code = "x = 1\n"
    pre = _render({"code": code, "lang": "python"})
    code_el = _code_element(pre)
    assert "language-python" in _class(code_el)
    assert len(code_el._children) > 0
    for child in code_el._children:
        assert child._tag_name == "span"
        assert not hasattr(child, "_html")


def test_codeblock_static_token_spans_are_direct_children_of_code() -> None:
    """Each token MUST render as a framework-managed <span class=\"tok-*\">
    direct child of <code>, with the token text as a text node and no wrapper."""
    pre = _render({"code": "def foo(): pass", "lang": "python"})
    code_el = _code_element(pre)
    assert len(code_el._children) > 0
    for child in code_el._children:
        assert child._tag_name == "span"
        assert not hasattr(child, "_html")
    first = code_el._children[0]
    assert _class(first) == "tok-kw k"
    assert isinstance(first._children[0], TextElement)
    assert first._children[0]._get_text() == "def"


def test_codeblock_reactive_path_uses_repeat_over_computed_tokens() -> None:
    """A Signal-backed ``code`` prop MUST take the reactive path: a
    RepeatElement over a computed token list derived from the signal."""
    sig = Signal("def foo(): pass")
    pre = _render({"code": sig, "lang": "python"})
    code_el = _code_element(pre)
    assert "language-python" in _class(code_el)
    rep = code_el._children[0]
    assert isinstance(rep, RepeatElement)
    assert isinstance(rep._sequence, Computed)
    assert isinstance(rep._sequence, SignalBase)
    tokens = rep._sequence.value
    assert any(t.type is TokenType.KEYWORD and t.value == "def" for t in tokens)


def test_codeblock_reactive_path_retokenizes_on_signal_update() -> None:
    """Updating the signal MUST re-tokenize the computed token list."""
    sig = Signal("def foo(): pass")
    pre = _render({"code": sig, "lang": "python"})
    code_el = _code_element(pre)
    rep = code_el._children[0]
    assert isinstance(rep, RepeatElement)
    sig.value = "x = 42"
    updated = rep._sequence.value
    assert any(t.type is TokenType.NUMBER and t.value == "42" for t in updated)
    assert not any(t.value == "def" for t in updated)


def test_codeblock_reactive_update_rerenders_token_spans() -> None:
    """A signal update MUST re-render the token spans through the render
    machinery: the RepeatElement rebuilds its children and the new tokens
    replace the old ones in the rendered output."""
    captured: dict[str, Any] = {}

    @define_component()
    def CodeBlockRenderPage(context):
        code = use_state(lambda: "def foo(): pass")
        captured["code"] = code
        return create_element(
            "div",
            {},
            CodeBlock({"code": code, "lang": "python"}),
        )

    with TestRenderer.render(CodeBlockRenderPage) as result:
        code_el = result.query_selector("code")
        assert code_el is not None
        assert code_el.getAttribute("class") == "language-python"
        initial_classes = [span.getAttribute("class") for span in code_el.childNodes]
        assert len(initial_classes) > 0
        assert all(c is not None and c.startswith("tok-") for c in initial_classes)
        assert result.find_by_text("def") is not None

        captured["code"].value = "x = 42"
        scheduler = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
        run_sync(scheduler.drain())

        assert result.find_by_text("42") is not None
        assert result.find_by_text("def") is None
        code_el = result.query_selector("code")
        assert code_el is not None
        updated_classes = [span.getAttribute("class") for span in code_el.childNodes]
        assert len(updated_classes) > 0
        assert "tok-num m" in updated_classes


def test_codeblock_unknown_language_renders_single_tok_ident_span() -> None:
    """Unknown languages MUST render a single <span class=\"tok-ident\"> child
    and MUST NOT raise LexerNotFoundError."""
    pre = _render({"code": "x = 1", "lang": "nonexistent-language"})
    code_el = _code_element(pre)
    assert len(code_el._children) == 1
    span = code_el._children[0]
    assert span._tag_name == "span"
    assert _class(span) == "tok-ident"
    assert isinstance(span._children[0], TextElement)
    assert span._children[0]._get_text() == "x = 1"


def test_codeblock_unknown_language_keeps_raw_text() -> None:
    """The fallback span MUST carry the raw code as text; HTML escaping is the
    renderer's structural responsibility (text nodes), not manual escaping."""
    code = "<script>alert(1)</script>"
    pre = _render({"code": code, "lang": "nope"})
    code_el = _code_element(pre)
    span = code_el._children[0]
    assert _class(span) == "tok-ident"
    assert span._children[0]._get_text() == code


def test_codeblock_empty_code_renders_no_children() -> None:
    """Empty code MUST render no children under <code> (no wrapper span)."""
    pre = _render({"code": "", "lang": "python"})
    code_el = _code_element(pre)
    assert len(code_el._children) == 0


def test_codeblock_empty_code_unknown_language_renders_no_children() -> None:
    """The empty-code early return MUST take precedence over the fallback."""
    pre = _render({"code": "", "lang": "nonexistent-language"})
    code_el = _code_element(pre)
    assert len(code_el._children) == 0


class _NoTokenLexer:
    name = "no-token-lexer"
    aliases: tuple[str, ...] = ()
    file_extensions: tuple[str, ...] = ()

    def tokenize(self, code: str):
        return iter(())


def test_codeblock_no_tokens_falls_back_to_single_tok_ident_span() -> None:
    """A registered lexer returning no tokens MUST render the same single
    <span class=\"tok-ident\"> fallback as an unknown language."""
    register_lexer(_NoTokenLexer())
    pre = _render({"code": "x = 1", "lang": "no-token-lexer"})
    code_el = _code_element(pre)
    assert len(code_el._children) == 1
    span = code_el._children[0]
    assert span._tag_name == "span"
    assert _class(span) == "tok-ident"
    assert span._children[0]._get_text() == "x = 1"


def test_codeblock_spans_match_highlight_output() -> None:
    """The component's structured spans MUST match highlight() output span for
    span in both class string and text content (drift guard)."""
    code = "def foo():\n    return 42  # answer"
    pre = _render({"code": code, "lang": "python"})
    code_el = _code_element(pre)
    component_classes = [_class(c) for c in code_el._children]
    component_texts = [c._children[0]._get_text() for c in code_el._children]
    highlight_spans = _SPAN_RE.findall(highlight(code, "python"))
    assert component_classes == [cls for cls, _ in highlight_spans]
    assert component_texts == [html_module.unescape(txt) for _, txt in highlight_spans]


@pytest.mark.parametrize(
    ("code", "lang"),
    [
        ('echo "hi"', "bash"),
        ('key = "value"', "toml"),
        ("x = 1", "nonexistent-language"),
    ],
)
def test_codeblock_spans_match_highlight_output_other_langs(code: str, lang: str) -> None:
    pre = _render({"code": code, "lang": lang})
    code_el = _code_element(pre)
    component_classes = [_class(c) for c in code_el._children]
    component_texts = [c._children[0]._get_text() for c in code_el._children]
    highlight_spans = _SPAN_RE.findall(highlight(code, lang))
    assert component_classes == [cls for cls, _ in highlight_spans]
    assert component_texts == [html_module.unescape(txt) for _, txt in highlight_spans]


class _FakeClipboardHostPort(FakeBrowserHostPort):
    def __init__(self, dom_port: FakeBrowserDOMPort | None = None) -> None:
        super().__init__(dom_port)
        self.copied_texts: list[str] = []

    def create_js_global_getter(self, name: str, *, wrapper: Any = None, default: Any = None) -> Any:
        if name == "navigator":
            copied = self.copied_texts

            class _Clipboard:
                def writeText(self, text: str) -> None:
                    copied.append(text)

            nav = type("FakeNavigator", (), {"clipboard": _Clipboard()})()
            return lambda: wrapper(nav) if wrapper is not None else nav
        return super().create_js_global_getter(name, wrapper=wrapper, default=default)


def test_codeblock_default_omits_copy_chrome() -> None:
    @define_component()
    def DefaultHost(context):
        return CodeBlock({"code": "x = 1", "lang": "python"})

    with TestRenderer.render(DefaultHost) as result:
        assert result.query_selector("button") is None
        pre = result.query_selector("pre")
        assert pre is not None
        assert "code-block" in (pre.getAttribute("class") or "").split()


def test_codeblock_copyable_renders_button_and_preserves_direct_token_spans() -> None:
    sig = Signal("x = 1")

    @define_component()
    def CopyableHost(context):
        return create_element(
            "div",
            {},
            CodeBlock({"code": "def foo(): pass", "lang": "python", "copyable": True}),
            CodeBlock({"code": sig, "lang": "python", "copyable": True}),
        )

    with TestRenderer.render(CopyableHost) as result:
        fake_host = _FakeClipboardHostPort()
        result._scope.provide(HOST_PORT_KEY, fake_host)

        buttons = result.query_selector_all("button")
        assert len(buttons) == 2
        assert buttons[0].getAttribute("class") == "code-block-copy"
        assert buttons[0].getAttribute("aria-label") == "Copy code"
        assert buttons[0].getAttribute("data-copied") == "false"
        assert buttons[0].textContent == "Copy"

        codes = result.query_selector_all("code")
        assert len(codes) == 2
        for code_el in codes:
            assert len(code_el.childNodes) > 0
            for child in code_el.childNodes:
                assert child.nodeName.lower() == "span"
                assert "tok-" in (child.getAttribute("class") or "")

        buttons[0].dispatchEvent(VirtualDOMEvent("click"))
        assert fake_host.copied_texts == ["def foo(): pass"]
        assert buttons[0].textContent == "Copied"
        assert buttons[0].getAttribute("aria-label") == "Copied to clipboard"
        assert buttons[0].getAttribute("data-copied") == "true"

        sig.value = "y = 42"
        scheduler = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
        run_sync(scheduler.drain())
        buttons[1].dispatchEvent(VirtualDOMEvent("click"))
        assert fake_host.copied_texts == ["def foo(): pass", "y = 42"]
