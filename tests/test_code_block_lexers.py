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


_ROUND_TRIP_SAMPLES = [
    "class Counter:\n    def __init__(self):\n        self.count = 0\n",
    '@dataclass\nclass ChatMessage:\n    user: str\n\nws = use_websocket("/api/chat")\n',
    "class Event:\n    type: str\n",
    "class Foo(Bar):\n    pass\n",
    "def foo(): pass",
    "async def fetch():\n    return 1\n",
    "x = a[0] + f(b, c)\n",
]


@pytest.mark.parametrize("code", _ROUND_TRIP_SAMPLES)
def test_python_lexer_round_trip(code: str) -> None:
    tokens = list(PythonLexer().tokenize(code))
    assert "".join(t.value for t in tokens) == code


def test_python_lexer_class_name_stays_in_place() -> None:
    code = "class Counter:\n    def __init__(self):\n        self.count = 0\n"
    tokens = list(PythonLexer().tokenize(code))
    assert "".join(t.value for t in tokens) == code
    assert [t.value for t in tokens if t.type is TokenType.FUNCTION] == ["Counter", "__init__"]
    values = [t.value for t in tokens]
    assert values.index("Counter") < values.index(":")


def test_python_lexer_class_name_not_displaced_by_later_call() -> None:
    code = '@dataclass\nclass ChatMessage:\n    user: str\n\nws = use_websocket("/api/chat")\n'
    tokens = list(PythonLexer().tokenize(code))
    assert "".join(t.value for t in tokens) == code
    values = [t.value for t in tokens]
    assert values.index("ChatMessage") < values.index(":")
    function_tokens = [t for t in tokens if t.type is TokenType.FUNCTION]
    assert [t.value for t in function_tokens] == ["ChatMessage"]


def test_python_lexer_class_only_not_appended_at_eof() -> None:
    code = "class Event:\n    type: str\n"
    tokens = list(PythonLexer().tokenize(code))
    assert "".join(t.value for t in tokens) == code
    assert tokens[-1].value != "Event"


def test_python_lexer_class_with_bases_highlights_name() -> None:
    tokens = list(PythonLexer().tokenize("class Foo(Bar):\n    pass\n"))
    assert any(t.type is TokenType.FUNCTION and t.value == "Foo" for t in tokens)
    assert any(t.type is TokenType.IDENTIFIER and t.value == "Bar" for t in tokens)


def test_python_lexer_def_statement_key_parts() -> None:
    tokens = list(PythonLexer().tokenize("def foo(): pass"))
    assert tokens[0] == Token(TokenType.KEYWORD, "def")
    assert tokens[2] == Token(TokenType.FUNCTION, "foo")
    assert all(t.type is TokenType.PUNCTUATION for t in tokens if t.value in ("(", ")", ":"))


def test_python_lexer_punctuation_vs_operator() -> None:
    tokens = list(PythonLexer().tokenize("x = a[0] + f(b, c)\n"))
    assert all(t.type is TokenType.PUNCTUATION for t in tokens if t.value in ("(", ")", "[", "]", ",", ":"))
    assert all(t.type is TokenType.OPERATOR for t in tokens if t.value in ("=", "+"))
    assert "".join(t.value for t in tokens) == "x = a[0] + f(b, c)\n"


def test_python_lexer_fstring_literal_is_string() -> None:
    code = 'msg = f"hello {name}"\n'
    tokens = list(PythonLexer().tokenize(code))
    assert [t.value for t in tokens if t.type is TokenType.STRING] == ['f"', "hello ", '"']
    assert any(t.type is TokenType.IDENTIFIER and t.value == "name" for t in tokens)
    assert "".join(t.value for t in tokens) == code


def test_python_lexer_match_as_variable() -> None:
    tokens = list(PythonLexer().tokenize("match = re.match(pattern, text)\n"))
    assert all(t.type is not TokenType.KEYWORD for t in tokens if t.value == "match")


def test_python_lexer_match_statement_keyword() -> None:
    tokens = list(PythonLexer().tokenize("match command:\n    case _: pass\n"))
    keywords = [t for t in tokens if t.type is TokenType.KEYWORD]
    assert keywords[0].value == "match"
    assert keywords[1].value == "case"


def test_python_lexer_type_is_builtin() -> None:
    tokens = list(PythonLexer().tokenize("t = type(obj)\n"))
    assert any(t.type is TokenType.BUILTIN and t.value == "type" for t in tokens)


def test_python_lexer_underscore_is_identifier() -> None:
    tokens = list(PythonLexer().tokenize("for _ in range(3):\n    pass\n"))
    assert any(t.type is TokenType.IDENTIFIER and t.value == "_" for t in tokens)


def test_python_lexer_matmul_is_not_decorator() -> None:
    tokens = list(PythonLexer().tokenize("c = a @ b\n"))
    assert all(t.type is not TokenType.DECORATOR for t in tokens)
    assert any(t.type is TokenType.OPERATOR and t.value == "@" for t in tokens)


def test_python_lexer_def_named_match_is_function() -> None:
    tokens = list(PythonLexer().tokenize("def match(x):\n    pass\n"))
    assert any(t.type is TokenType.FUNCTION and t.value == "match" for t in tokens)


def test_python_lexer_match_before_hard_keyword_is_identifier() -> None:
    samples = [
        "for match in re.finditer(pattern, text):\n    pass\n",
        "with match as m:\n    pass\n",
        "x = match and y\n",
    ]
    for code in samples:
        tokens = list(PythonLexer().tokenize(code))
        assert all(t.type is not TokenType.KEYWORD for t in tokens if t.value == "match")


def test_python_lexer_case_literal_patterns_keep_keyword() -> None:
    tokens = list(PythonLexer().tokenize('match point:\n    case None: pass\n    case 1: pass\n    case "a": pass\n'))
    keywords = [t for t in tokens if t.type is TokenType.KEYWORD]
    assert any(t.value == "match" for t in keywords)
    assert sum(1 for t in keywords if t.value == "case") == 3


def test_python_lexer_match_at_line_end_is_identifier() -> None:
    samples = [
        "x = match\nprint(x)\n",
        "x = case\nprint(x)\n",
    ]
    for code in samples:
        tokens = list(PythonLexer().tokenize(code))
        assert all(t.type is not TokenType.KEYWORD for t in tokens if t.value in ("match", "case"))


def test_python_lexer_def_shadowing_builtin_is_function() -> None:
    tokens = list(PythonLexer().tokenize("def type(x):\n    return x\n"))
    assert any(t.type is TokenType.FUNCTION and t.value == "type" for t in tokens)
    assert all(t.type is not TokenType.BUILTIN for t in tokens if t.value == "type")


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
    assert any(t.type == TokenType.IDENTIFIER and t.value == "$HOME" for t in tokens)


def test_bash_lexer_tokenizes_braced_variable() -> None:
    lexer = BashLexer()
    tokens = list(lexer.tokenize("echo ${PATH}"))
    assert any(t.type == TokenType.IDENTIFIER and t.value == "${PATH}" for t in tokens)


def test_bash_lexer_tokenizes_comment() -> None:
    lexer = BashLexer()
    tokens = list(lexer.tokenize("# this is a comment\necho hi"))
    assert any(t.type == TokenType.COMMENT and t.value.startswith("#") for t in tokens)


def test_bash_lexer_positional_parameter_single_token() -> None:
    tokens = list(BashLexer().tokenize("echo $1"))
    assert any(t.type is TokenType.IDENTIFIER and t.value == "$1" for t in tokens)


def test_bash_lexer_dollar_ten_is_positional_plus_digit() -> None:
    tokens = list(BashLexer().tokenize("echo $10"))
    values = [t.value for t in tokens]
    assert "$1" in values
    assert "0" in values


def test_bash_lexer_special_variables_single_tokens() -> None:
    tokens = list(BashLexer().tokenize("echo $$ $@ $? $# $! $- $*"))
    variables = [t.value for t in tokens if t.type is TokenType.IDENTIFIER and t.value.startswith("$")]
    assert variables == ["$$", "$@", "$?", "$#", "$!", "$-", "$*"]


def test_bash_lexer_hash_in_word_is_not_comment() -> None:
    code = "echo a#b\n"
    tokens = list(BashLexer().tokenize(code))
    assert all(t.type is not TokenType.COMMENT for t in tokens)
    assert "".join(t.value for t in tokens) == code


def test_bash_lexer_comment_after_whitespace() -> None:
    tokens = list(BashLexer().tokenize("echo a # b\n"))
    assert any(t.type is TokenType.COMMENT and t.value == "# b" for t in tokens)


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


def test_toml_lexer_date_does_not_swallow_comment() -> None:
    tokens = list(TomlLexer().tokenize("d = 2024-01-01  # release date\n"))
    assert any(t.type is TokenType.STRING and t.value == "2024-01-01" for t in tokens)
    assert any(t.type is TokenType.COMMENT and t.value == "# release date" for t in tokens)
    assert "".join(t.value for t in tokens) == "d = 2024-01-01  # release date\n"


def test_toml_lexer_full_datetime_single_string() -> None:
    tokens = list(TomlLexer().tokenize("t = 2024-01-01T10:20:30Z\n"))
    assert any(t.type is TokenType.STRING and t.value == "2024-01-01T10:20:30Z" for t in tokens)


def test_toml_lexer_hex_octal_binary_numbers() -> None:
    for literal in ("0x10", "0o17", "0b101"):
        tokens = list(TomlLexer().tokenize(f"v = {literal}\n"))
        assert any(t.type is TokenType.NUMBER and t.value == literal for t in tokens)


def test_toml_lexer_underscored_integer() -> None:
    tokens = list(TomlLexer().tokenize("n = 1_000_000\n"))
    assert any(t.type is TokenType.NUMBER and t.value == "1_000_000" for t in tokens)


def test_toml_lexer_round_trip() -> None:
    code = 'd = 2024-01-01  # release\nmask = 0x10\nt = 2024-01-01T10:20:30Z\nname = "x"\n'
    tokens = list(TomlLexer().tokenize(code))
    assert "".join(t.value for t in tokens) == code


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
