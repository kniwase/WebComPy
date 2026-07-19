from __future__ import annotations

from dataclasses import dataclass

import pytest

from webcompy.signal import Signal
from webcompy.template._holes import (
    HOLE_PATTERN,
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


class TestHolePattern:
    def test_matches_simple_variable(self):
        match = HOLE_PATTERN.search("{{ name }}")
        assert match is not None
        assert match.group(1) == "name"

    def test_matches_no_whitespace(self):
        match = HOLE_PATTERN.search("{{name}}")
        assert match is not None
        assert match.group(1) == "name"

    def test_matches_extra_whitespace(self):
        match = HOLE_PATTERN.search("{{   name   }}")
        assert match is not None
        assert match.group(1) == "name"

    def test_matches_dotted_path(self):
        match = HOLE_PATTERN.search("{{ user.name }}")
        assert match is not None
        assert match.group(1) == "user.name"

    def test_matches_deep_dotted_path(self):
        match = HOLE_PATTERN.search("{{ a.b.c.d }}")
        assert match is not None
        assert match.group(1) == "a.b.c.d"

    def test_matches_underscore_start(self):
        match = HOLE_PATTERN.search("{{ _private }}")
        assert match is not None
        assert match.group(1) == "_private"

    def test_rejects_digit_first(self):
        assert HOLE_PATTERN.search("{{ 123 }}") is None

    def test_rejects_empty_braces(self):
        assert HOLE_PATTERN.search("{{}}") is None
        assert HOLE_PATTERN.search("{{ }}") is None

    def test_rejects_unclosed(self):
        assert HOLE_PATTERN.search("{{ name") is None

    def test_rejects_digit_first_segment_in_path(self):
        assert HOLE_PATTERN.search("{{ a.1b }}") is None


class TestSplitText:
    def test_literal_only(self):
        result = split_text("hello world")
        assert result == [LiteralText("hello world")]

    def test_hole_only(self):
        result = split_text("{{ name }}")
        assert result == [Hole("name")]

    def test_mixed_leading_literal_then_hole(self):
        result = split_text("hello {{ name }}")
        assert result == [LiteralText("hello "), Hole("name")]

    def test_mixed_trailing_literal(self):
        result = split_text("{{ name }} done")
        assert result == [Hole("name"), LiteralText(" done")]

    def test_multiple_holes(self):
        result = split_text("{{ a }} and {{ b }}")
        assert result == [Hole("a"), LiteralText(" and "), Hole("b")]

    def test_dotted_path(self):
        result = split_text("{{ user.name }}")
        assert result == [Hole("user.name")]

    def test_empty_string(self):
        assert split_text("") == []

    def test_only_literals_around_no_match(self):
        assert split_text("{{123}}") == [LiteralText("{{123}}")]


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
