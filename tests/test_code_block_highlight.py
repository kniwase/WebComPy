from __future__ import annotations

import dataclasses

import pytest

from webcompy.ui.code_block import (
    Token,
    TokenType,
    highlight,
)
from webcompy.ui.code_block.lexers._registry import (
    LexerNotFoundError,
    register_builtin_lexers,
)


@pytest.fixture(autouse=True)
def _ensure_lexers() -> None:
    register_builtin_lexers()


def test_highlight_empty_input() -> None:
    assert highlight("", "python") == ""


def test_highlight_escapes_html_in_input() -> None:
    out = highlight("x = '<script>'", "python")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_highlight_unknown_language_raises() -> None:
    with pytest.raises(LexerNotFoundError):
        highlight("x = 1", "nonexistent-language")


def test_highlight_includes_tok_class() -> None:
    out = highlight("def foo(): pass", "python")
    assert 'class="tok-kw' in out


def test_highlight_includes_pygments_short_class() -> None:
    out = highlight("def foo(): pass", "python")
    assert 'class="tok-kw k"' in out


def test_highlight_keyword_class_order() -> None:
    out = highlight("def foo(): pass", "python")
    assert 'class="tok-kw k">def</span>' in out


def test_highlight_string_class() -> None:
    out = highlight('x = "hi"', "python")
    assert 'class="tok-str s"' in out


def test_highlight_comment_class() -> None:
    out = highlight("# comment", "python")
    assert 'class="tok-comment c"' in out


def test_highlight_number_class() -> None:
    out = highlight("x = 42", "python")
    assert 'class="tok-num m"' in out


def test_highlight_identifier_has_no_pygments_short_class() -> None:
    out = highlight("def foo(): pass", "python")
    assert "tok-ident" in out
    assert 'class="tok-ident "' not in out


def test_highlight_function_name_class() -> None:
    out = highlight("def foo(): pass", "python")
    assert 'class="tok-fn nf"' in out


def test_highlight_decorator_class() -> None:
    out = highlight("@property\ndef x(self): pass", "python")
    assert 'class="tok-decorator nd"' in out


def test_highlight_bash_known_language() -> None:
    out = highlight('echo "hi"', "bash")
    assert 'class="tok-string' not in out or 'class="tok-str' in out
    assert "<span" in out


def test_highlight_toml_known_language() -> None:
    out = highlight('key = "value"', "toml")
    assert "<span" in out
    assert 'class="tok-str' in out


def test_token_is_immutable() -> None:
    token = Token(TokenType.KEYWORD, "def")
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        token.type = TokenType.STRING  # type: ignore[misc]
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        token.value = "else"  # type: ignore[misc]


class _FakePygmentsLexer:
    name = "fake"
    aliases = ("fake",)
    filenames: tuple[str, ...] = ()

    def get_tokens(self, code: str):
        from pygments.token import Keyword, Name, String

        return [
            ("def", Keyword),
            (" ", Name),
            ("f", Name.Function),
            ('"', String),
            ("hi", String),
        ]


def test_pygments_adapter_break_is_under_if() -> None:
    """The Pygments adapter's inner loop must break only when the
    ``if pygtok in src:`` condition matches. Regression test for the
    unconditional-break bug flagged by the PR #178 review."""
    from webcompy.ui.code_block.lexers._adapters._pygments import (
        PygmentsLexerWrapper,
    )

    wrapper = PygmentsLexerWrapper(_FakePygmentsLexer())
    tokens = list(wrapper.tokenize('def f"hi"'))
    types = [(t.type, t.value) for t in tokens]
    assert (TokenType.KEYWORD, "def") in types
    assert any(t.type == TokenType.FUNCTION and t.value == "f" for t in tokens)
    assert any(t.type == TokenType.STRING and t.value == "hi" for t in tokens)
    assert all(t.type is not TokenType.KEYWORD for t in tokens if t.value == "hi")
