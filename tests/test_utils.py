from webcompy.utils._environment import ENVIRONMENT
from webcompy.utils._serialize import is_json_seriarizable
from webcompy.utils._text import strip_multiline_text


def test_environment_is_other():
    assert ENVIRONMENT == "other"


def test_is_json_seriarizable_dict():
    assert is_json_seriarizable({"a": 1, "b": "hello"}) is True


def test_is_json_seriarizable_nested():
    assert is_json_seriarizable({"a": [1, 2, {"b": "x"}]}) is True


def test_is_json_seriarizable_non_string_key():
    assert is_json_seriarizable({1: "a"}) is False


def test_is_json_seriarizable_non_serializable_value():
    assert is_json_seriarizable({"a": {1, 2}}) is False


def test_is_json_seriarizable_list():
    assert is_json_seriarizable([1, "hello", True, None]) is True


def test_is_json_seriarizable_str():
    assert is_json_seriarizable("hello") is False


def test_is_json_seriarizable_int():
    assert is_json_seriarizable(42) is False


def test_is_json_seriarizable_none():
    assert is_json_seriarizable(None) is False


def test_is_json_seriarizable_bool():
    assert is_json_seriarizable(True) is False


def test_is_json_seriarizable_float():
    assert is_json_seriarizable(3.14) is False


def test_strip_multiline_text_removes_blank_lines():
    text = "\n\n  hello\n  world"
    result = strip_multiline_text(text)
    assert result.startswith("hello")


def test_strip_multiline_text_dedents():
    text = "    line1\n    line2\n    line3"
    result = strip_multiline_text(text)
    assert result == "line1\nline2\nline3"


def test_strip_multiline_text_empty():
    assert strip_multiline_text("") == ""
