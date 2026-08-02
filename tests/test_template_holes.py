from __future__ import annotations

from dataclasses import dataclass

import pytest

from webcompy.exception import WebComPyException
from webcompy.signal import Computed, Signal
from webcompy.template._holes import (
    Hole,
    LiteralText,
    resolve_holes,
    resolve_var,
    split_text,
)


@dataclass
class SampleUser:
    name: str
    age: int


class TestSplitText:
    def test_literal_only(self):
        result = split_text("hello world")
        assert result == [LiteralText("hello world")]

    def test_hole_only(self):
        result = split_text("{{ name }}")
        assert len(result) == 1
        assert isinstance(result[0], Hole)
        assert result[0].expr_source == "name"

    def test_mixed_leading_literal_then_hole(self):
        result = split_text("hello {{ name }}")
        assert len(result) == 2
        assert isinstance(result[0], LiteralText)
        assert result[0].text == "hello "
        assert isinstance(result[1], Hole)
        assert result[1].expr_source == "name"

    def test_mixed_trailing_literal(self):
        result = split_text("{{ name }} done")
        assert len(result) == 2
        assert isinstance(result[0], Hole)
        assert result[0].expr_source == "name"
        assert isinstance(result[1], LiteralText)
        assert result[1].text == " done"

    def test_multiple_holes(self):
        result = split_text("{{ a }} and {{ b }}")
        assert len(result) == 3
        assert isinstance(result[0], Hole)
        assert result[0].expr_source == "a"
        assert isinstance(result[1], LiteralText)
        assert result[1].text == " and "
        assert isinstance(result[2], Hole)
        assert result[2].expr_source == "b"

    def test_dotted_path(self):
        result = split_text("{{ user.name }}")
        assert len(result) == 1
        assert isinstance(result[0], Hole)
        assert result[0].plan.is_plain_path

    def test_expression(self):
        result = split_text("{{ count + 1 }}")
        assert len(result) == 1
        assert isinstance(result[0], Hole)
        assert not result[0].plan.is_plain_path

    def test_nested_dict_literal(self):
        result = split_text('{{ {"a": {"b": 2}}["a"]["b"] }}')
        assert len(result) == 1
        assert isinstance(result[0], Hole)
        assert result[0].expr_source == '{"a": {"b": 2}}["a"]["b"]'

    def test_empty_string(self):
        assert split_text("") == []

    def test_unclosed_raises_in_strict(self):
        with pytest.raises(WebComPyException):
            split_text("{{ unclosed", strict=True)

    def test_unclosed_literal_in_non_strict(self):
        result = split_text("{{unclosed")
        assert result == [LiteralText("{{unclosed")]

    def test_integer_literal_hole(self):
        result = split_text("{{123}}")
        assert len(result) == 1
        assert isinstance(result[0], Hole)
        assert result[0].expr_source == "123"

    def test_invalid_expression_raises_in_strict(self):
        with pytest.raises(WebComPyException):
            split_text("{{ count + }}", strict=True)

    def test_unbalanced_rbrace_literal_in_non_strict(self):
        result = split_text("{{ } x")
        assert result == [LiteralText("{{ } x")]

    def test_unbalanced_rbrace_raises_in_strict(self):
        with pytest.raises(WebComPyException):
            split_text("{{ } x }}", strict=True)

    def test_invalid_expression_literal_in_non_strict(self):
        result = split_text("{{ count + }}")
        # In non-strict, invalid expression stays literal
        assert result == [LiteralText("{{ count + }}")]


class TestResolveVar:
    def test_dict_key_access(self):
        assert resolve_var("name", {"name": "Alice"}) == "Alice"

    def test_dict_chained_access(self):
        ctx = {"user": {"name": "Bob", "age": 30}}
        assert resolve_var("user.name", ctx) == "Bob"
        assert resolve_var("user.age", ctx) == 30

    def test_object_attribute_access(self):
        user = SampleUser(name="Charlie", age=25)
        assert resolve_var("user.name", {"user": user}) == "Charlie"
        assert resolve_var("user.age", {"user": user}) == 25

    def test_chained_object_access(self):
        user = SampleUser(name="Dave", age=40)
        ctx = {"outer": {"inner": user}}
        assert resolve_var("outer.inner.name", ctx) == "Dave"

    def test_signal_intermediate_unwrapped_for_dict(self):
        ctx = {"user": Signal({"name": "Bob"})}
        result = resolve_var("user.name", ctx)
        assert isinstance(result, Computed)
        assert result.value == "Bob"

    def test_signal_intermediate_unwrapped_for_object(self):
        ctx = {"user": Signal(SampleUser(name="Charlie", age=25))}
        result = resolve_var("user.name", ctx)
        assert isinstance(result, Computed)
        assert result.value == "Charlie"
        assert resolve_var("user.age", ctx).value == 25

    def test_final_signal_preserved(self):
        sig = Signal("Alice")
        assert resolve_var("user", {"user": sig}) is sig

    def test_missing_dict_key_raises(self):
        with pytest.raises(KeyError, match="missing"):
            resolve_var("missing", {"name": "x"})

    def test_missing_attribute_raises(self):
        with pytest.raises(KeyError, match="age"):
            resolve_var("age", {"user": SampleUser(name="x", age=0)})

    def test_top_level_missing_dict_key(self):
        with pytest.raises(KeyError):
            resolve_var("foo", {})


class TestResolveHoles:
    def test_passthrough_plain_string(self):
        assert resolve_holes("hello", {}) == "hello"

    def test_passthrough_literal_only_with_context(self):
        assert resolve_holes("hello world", {"x": "y"}) == "hello world"

    def test_signal_value_extraction(self):
        sig = Signal("dynamic")
        assert resolve_holes("{{ val }}", {"val": sig}) == "dynamic"

    def test_none_value_renders_empty(self):
        assert resolve_holes("{{ val }}", {"val": None}) == ""

    def test_signal_none_renders_empty(self):
        sig = Signal(None)
        assert resolve_holes("{{ val }}", {"val": sig}) == ""

    def test_signal_none_mixed_with_literal_renders_literal_only(self):
        sig = Signal(None)
        assert resolve_holes("count: {{ n }}", {"n": sig}) == "count: "

    def test_int_renders_via_str(self):
        assert resolve_holes("{{ n }}", {"n": 42}) == "42"

    def test_mixed_literal_and_hole(self):
        assert resolve_holes("count is {{ n }}", {"n": 5}) == "count is 5"

    def test_css_style_mixed(self):
        assert (
            resolve_holes("color: {{ color }}; size: {{ size }};", {"color": "red", "size": "10px"})
            == "color: red; size: 10px;"
        )

    def test_multiple_holes_mixed(self):
        assert resolve_holes("{{ a }} + {{ b }} = {{ c }}", {"a": 1, "b": 2, "c": 3}) == "1 + 2 = 3"

    def test_dotted_path_in_css(self):
        ctx = {"theme": {"primary": "#007bff"}}
        assert resolve_holes("background: {{ theme.primary }};", ctx) == "background: #007bff;"
