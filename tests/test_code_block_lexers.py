from __future__ import annotations

import pytest

from webcompy.ui.code_block._tokens import Token, TokenType
from webcompy.ui.code_block.lexers._bash import BashLexer
from webcompy.ui.code_block.lexers._python import PythonLexer
from webcompy.ui.code_block.lexers._registry import (
    LexerNotFoundError,
    get_lexer,
    list_lexers,
    register_builtin_lexers,
    register_lexer,
    reset_lexer_registry,
)
from webcompy.ui.code_block.lexers._toml import TomlLexer


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    reset_lexer_registry()


def test_python_lexer_tokenizes_keyword() -> None:
    lexer = PythonLexer()
    tokens = list(lexer.tokenize("def foo(): pass"))
    types = [t.type for t in tokens]
    assert TokenType.KEYWORD in types
    assert TokenType.FUNCTION in types
    assert any(t.type == TokenType.KEYWORD and t.value == "def" for t in tokens)


def test_python_lexer_tokenizes_string_and_comment() -> None:
    lexer = PythonLexer()
    code = 'x = "hello"  # greet'
    tokens = list(lexer.tokenize(code))
    assert any(t.type == TokenType.STRING and '"hello"' in t.value for t in tokens)
    assert any(t.type == TokenType.COMMENT and "# greet" in t.value for t in tokens)


def test_python_lexer_tokenizes_number() -> None:
    lexer = PythonLexer()
    tokens = list(lexer.tokenize("count = 42"))
    assert any(t.type == TokenType.NUMBER and t.value == "42" for t in tokens)


def test_python_lexer_tokenizes_decorator() -> None:
    lexer = PythonLexer()
    tokens = list(lexer.tokenize("@property\ndef x(self): pass"))
    assert any(t.type == TokenType.DECORATOR and t.value == "property" for t in tokens)


def test_python_lexer_handles_invalid_input_gracefully() -> None:
    lexer = PythonLexer()
    tokens = list(lexer.tokenize("def !!!"))
    assert tokens
    assert all(isinstance(t, Token) for t in tokens)


def test_python_lexer_preserves_newlines_between_statements() -> None:
    lexer = PythonLexer()
    code = "# header\nimport os\nx = 1\n"
    tokens = list(lexer.tokenize(code))
    newline_tokens = [t for t in tokens if t.value == "\n" and t.type == TokenType.IDENTIFIER]
    assert len(newline_tokens) == 3


def test_python_lexer_preserves_newline_after_comment() -> None:
    lexer = PythonLexer()
    tokens = list(lexer.tokenize("# webcompy_config.py\nimport app.app as a\n"))
    values = [t.value for t in tokens]
    comment_idx = values.index("# webcompy_config.py")
    assert values[comment_idx + 1] == "\n"


def test_highlight_preserves_newlines_for_python_multiline() -> None:
    from webcompy.ui.code_block._highlight import highlight

    register_lexer(PythonLexer())
    code = "# webcompy_config.py\nimport app.app as a\n"
    rendered = highlight(code, "python")
    newline_count = rendered.count("\n")
    assert newline_count >= 2
    assert "# webcompy_config.py" in rendered
    assert "import" in rendered


def test_bash_lexer_tokenizes_keyword_and_string() -> None:
    lexer = BashLexer()
    tokens = list(lexer.tokenize('if [ "$x" = "y" ]; then echo ok; fi'))
    types = [t.type for t in tokens]
    assert TokenType.KEYWORD in types
    assert TokenType.STRING in types
    assert TokenType.BUILTIN in types


def test_bash_lexer_tokenizes_variable() -> None:
    lexer = BashLexer()
    tokens = list(lexer.tokenize("echo $HOME"))
    assert any(t.type == TokenType.DECORATOR and "$HOME" in t.value for t in tokens)


def test_bash_lexer_tokenizes_comment() -> None:
    lexer = BashLexer()
    tokens = list(lexer.tokenize("# this is a comment\necho hi"))
    assert any(t.type == TokenType.COMMENT and t.value.startswith("#") for t in tokens)


def test_bash_lexer_empty_input() -> None:
    lexer = BashLexer()
    assert list(lexer.tokenize("")) == []


def test_toml_lexer_tokenizes_section_and_key() -> None:
    lexer = TomlLexer()
    code = '[package]\nname = "webcompy"\nversion = "0.1.0"\n'
    tokens = list(lexer.tokenize(code))
    types = [t.type for t in tokens]
    assert TokenType.KEYWORD in types
    assert TokenType.STRING in types
    assert TokenType.OPERATOR in types


def test_toml_lexer_tokenizes_boolean() -> None:
    lexer = TomlLexer()
    tokens = list(lexer.tokenize("debug = true"))
    assert any(t.type == TokenType.KEYWORD and t.value == "true" for t in tokens)


def test_toml_lexer_tokenizes_number() -> None:
    lexer = TomlLexer()
    tokens = list(lexer.tokenize("port = 8080"))
    assert any(t.type == TokenType.NUMBER and t.value == "8080" for t in tokens)


def test_toml_lexer_tokenizes_comment() -> None:
    lexer = TomlLexer()
    tokens = list(lexer.tokenize("# top-level comment\nname = 'x'"))
    assert any(t.type == TokenType.COMMENT for t in tokens)


def test_registry_register_and_get_by_name() -> None:
    lexer = PythonLexer()
    register_lexer(lexer)
    assert get_lexer("python") is lexer


def test_registry_get_by_alias() -> None:
    register_lexer(PythonLexer())
    assert isinstance(get_lexer("py"), PythonLexer)


def test_registry_get_by_file_extension() -> None:
    register_lexer(PythonLexer())
    assert isinstance(get_lexer(".py"), PythonLexer)


def test_registry_unknown_raises() -> None:
    register_builtin_lexers()
    with pytest.raises(LexerNotFoundError):
        get_lexer("nonexistent-language")


def test_registry_list_lexers_returns_unique() -> None:
    register_builtin_lexers()
    names = [info.name for info in list_lexers()]
    assert names == sorted(set(names))
    assert "python" in names
    assert "bash" in names
    assert "toml" in names


def test_registry_register_builtin_idempotent() -> None:
    register_builtin_lexers()
    first = get_lexer("python")
    register_builtin_lexers()
    second = get_lexer("python")
    assert first is second


def test_registry_register_non_lexer_raises() -> None:
    with pytest.raises(TypeError):
        register_lexer("not a lexer")  # type: ignore[arg-type]


def test_registry_register_duplicate_raises_value_error() -> None:
    register_lexer(PythonLexer())
    with pytest.raises(ValueError, match="already registered"):
        register_lexer(PythonLexer())


def test_registry_register_duplicate_with_override_succeeds() -> None:
    original = PythonLexer()
    replacement = PythonLexer()
    register_lexer(original)
    register_lexer(replacement, override=True)
    assert get_lexer("python") is replacement


def test_registry_register_stores_source() -> None:
    register_lexer(PythonLexer(), source="pygments:python")
    info = next(i for i in list_lexers() if i.name == "python")
    assert info.source == "pygments:python"


def test_registry_register_default_source_is_custom() -> None:
    register_lexer(PythonLexer())
    info = next(i for i in list_lexers() if i.name == "python")
    assert info.source == "custom"


def test_registry_builtin_lexers_have_builtin_source() -> None:
    register_builtin_lexers()
    sources = {info.name: info.source for info in list_lexers()}
    assert sources["python"] == "builtin"
    assert sources["bash"] == "builtin"
    assert sources["toml"] == "builtin"


def test_lexer_info_has_source_field() -> None:
    from webcompy.ui.code_block.lexers._base import LexerInfo

    fields = LexerInfo.__dataclass_fields__
    assert "source" in fields
    assert "name" in fields
    assert "aliases" in fields
    assert "file_extensions" in fields


def test_registry_unknown_error_message_lists_available_lexers() -> None:
    register_builtin_lexers()
    with pytest.raises(LexerNotFoundError) as excinfo:
        get_lexer("nonexistent-language")
    message = str(excinfo.value)
    assert "python" in message
    assert "bash" in message
    assert "toml" in message


def test_registry_rejects_invalid_source_kwarg() -> None:
    """register_lexer must accept ``source`` only as a keyword argument."""
    with pytest.raises(TypeError):
        register_lexer(PythonLexer(), "pygments:python")  # type: ignore[misc]
