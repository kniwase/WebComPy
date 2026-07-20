from __future__ import annotations

import types
from pathlib import Path

import pytest

from webcompy.components._reactive_scoped_style import (
    ReactiveScopedStyle,
    ReactiveScopedStyleFunc,
    reactive_scoped_style,
)
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._keys import RESOURCE_PORT_KEY
from webcompy.resources import load_text
from webcompy.signal import Computed, Signal
from webcompy.template import css_text, css_text_template


@pytest.fixture
def port_scope():
    scope = DIScope()
    token = _active_di_scope.set(scope)
    yield scope
    _active_di_scope.reset(token)


class TestCssTextPlain:
    def test_returns_dict_for_plain_css(self):
        assert css_text(".btn { color: red; }") == {".btn": {"color": "red"}}

    def test_returns_empty_dict_for_empty_input(self):
        assert css_text("") == {}

    def test_returns_empty_dict_for_whitespace_only(self):
        assert css_text("   \n\t  ") == {}

    def test_returns_dict_for_at_rule(self):
        assert css_text("@media (max-width: 768px) { .btn { font-size: 12px; } }") == {
            "@media (max-width: 768px)": {".btn": {"font-size": "12px"}}
        }

    def test_returns_dict_for_keyframes(self):
        assert css_text("@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }") == {
            "@keyframes spin": {
                "0%": {"transform": "rotate(0deg)"},
                "100%": {"transform": "rotate(360deg)"},
            }
        }

    def test_returns_dict_for_nested_pseudo(self):
        assert css_text(".btn { color: red; :hover { background: blue; } }") == {
            ".btn": {
                "color": "red",
                ":hover": {"background": "blue"},
            }
        }


class TestCssTextAsyncCompose:
    @pytest.mark.asyncio
    async def test_css_text_composes_with_load_text(self, port_scope, tmp_path: Path):
        pkg = tmp_path / "app"
        pkg.mkdir()
        (pkg / "card.css").write_text(".btn { color: red; }", encoding="utf-8")

        from webcompy_server.ports._resource import ServerResourcePort

        port = ServerResourcePort(pkg, frozenset({"card.css"}))
        port_scope.provide(RESOURCE_PORT_KEY, port)

        text = await load_text("card.css")
        style = css_text(text)

        assert text == ".btn { color: red; }"
        assert style == {".btn": {"color": "red"}}

    @pytest.mark.asyncio
    async def test_server_resource_port_records_read_for_hydration(self, port_scope, tmp_path: Path):
        pkg = tmp_path / "app"
        pkg.mkdir()
        (pkg / "styles.css").write_text(".btn { color: red; }", encoding="utf-8")

        from webcompy_server.ports._resource import ServerResourcePort

        port = ServerResourcePort(pkg, frozenset({"styles.css"}))
        port_scope.provide(RESOURCE_PORT_KEY, port)

        text = await load_text("styles.css")
        css_text(text)

        recorded = port.get_recorded_resources()
        assert "styles.css" in recorded
        assert recorded["styles.css"] == b".btn { color: red; }"

    @pytest.mark.asyncio
    async def test_server_records_multiple_resource_reads(self, port_scope, tmp_path: Path):
        pkg = tmp_path / "app"
        pkg.mkdir()
        (pkg / "a.css").write_text(".a { color: red; }", encoding="utf-8")
        (pkg / "b.css").write_text(".b { color: blue; }", encoding="utf-8")

        from webcompy_server.ports._resource import ServerResourcePort

        port = ServerResourcePort(pkg, frozenset({"a.css", "b.css"}))
        port_scope.provide(RESOURCE_PORT_KEY, port)

        css_text(await load_text("a.css"))
        css_text(await load_text("b.css"))

        recorded = port.get_recorded_resources()
        assert set(recorded) == {"a.css", "b.css"}
        assert recorded["a.css"] == b".a { color: red; }"
        assert recorded["b.css"] == b".b { color: blue; }"

    @pytest.mark.asyncio
    async def test_failed_load_is_not_recorded(self, port_scope, tmp_path: Path):
        pkg = tmp_path / "app"
        pkg.mkdir()
        (pkg / "exists.css").write_text(".x { color: red; }", encoding="utf-8")

        from webcompy.ports import ResourceNotFoundError
        from webcompy_server.ports._resource import ServerResourcePort

        port = ServerResourcePort(pkg, frozenset({"exists.css"}))
        port_scope.provide(RESOURCE_PORT_KEY, port)

        css_text(await load_text("exists.css"))
        assert "exists.css" in port.get_recorded_resources()

        with pytest.raises(ResourceNotFoundError):
            await load_text("missing.css")
        assert "missing.css" not in port.get_recorded_resources()


class TestCssTextTemplateHoleResolution:
    def test_plain_string_value(self):
        factory = css_text_template(".btn { color: {{ color }}; }", {"color": "red"})
        assert factory() == {".btn": {"color": "red"}}

    def test_signal_value_at_call_time(self):
        sig = Signal("blue")
        factory = css_text_template(".btn { color: {{ color }}; }", {"color": sig})
        assert factory() == {".btn": {"color": "blue"}}
        sig.value = "green"
        assert factory() == {".btn": {"color": "green"}}

    def test_dotted_path_in_dict(self):
        factory = css_text_template(
            ".btn { color: {{ theme.primary }}; }",
            {"theme": {"primary": "#007bff"}},
        )
        assert factory() == {".btn": {"color": "#007bff"}}

    def test_dotted_path_in_dataclass(self):
        from dataclasses import dataclass

        @dataclass
        class Theme:
            primary: str
            accent: str

        factory = css_text_template(
            ".btn { color: {{ theme.primary }}; background: {{ theme.accent }}; }",
            {"theme": Theme(primary="red", accent="blue")},
        )
        result = factory()
        assert result == {".btn": {"color": "red", "background": "blue"}}

    def test_none_value_renders_empty_string(self):
        factory = css_text_template(".btn { color: {{ color }}; }", {"color": None})
        assert factory() == {".btn": {"color": ""}}

    def test_signal_none_value_renders_empty(self):
        sig = Signal(None)
        factory = css_text_template(".btn { color: {{ color }}; }", {"color": sig})
        assert factory() == {".btn": {"color": ""}}

    def test_int_rendered_via_str(self):
        factory = css_text_template(".x { z-index: {{ z }}; }", {"z": 10})
        assert factory() == {".x": {"z-index": "10"}}

    def test_multiple_holes_in_different_properties(self):
        factory = css_text_template(
            ".btn { color: {{ c }}; background: {{ b }}; }",
            {"c": "red", "b": "blue"},
        )
        assert factory() == {".btn": {"color": "red", "background": "blue"}}

    def test_missing_variable_keyerror(self):
        factory = css_text_template(".btn { color: {{ missing }}; }", {})
        with pytest.raises(KeyError, match="missing"):
            factory()

    def test_no_holes_plain_text(self):
        factory = css_text_template(".btn { color: red; }", {})
        assert factory() == {".btn": {"color": "red"}}


class TestCssTextTemplateSignalTracking:
    def test_signal_change_produces_new_dict_via_reactive_scoped_style(self):
        color = Signal("blue")
        factory = css_text_template(".btn { color: {{ color }}; }", {"color": color})

        style = reactive_scoped_style(factory)
        style._bind("test-cid")

        assert style.dict_computed.value == {".btn": {"color": "blue"}}
        color.value = "red"
        assert style.dict_computed.value == {".btn": {"color": "red"}}

    def test_signal_change_produces_new_dict_via_computed(self):
        color = Signal("blue")
        factory = css_text_template(".btn { color: {{ color }}; }", {"color": color})

        computed = Computed(factory)

        assert computed.value == {".btn": {"color": "blue"}}
        color.value = "red"
        assert computed.value == {".btn": {"color": "red"}}

    def test_render_css_reflects_signal_change(self):
        color = Signal("blue")
        factory = css_text_template(".btn { color: {{ color }}; }", {"color": color})

        style = reactive_scoped_style(factory)
        style._bind("abc")

        out = style.render_css("abc")
        assert "color: blue" in out
        assert "color: red" not in out

        color.value = "red"

        out2 = style.render_css("abc")
        assert "color: red" in out2

    def test_multiple_signal_holes_tracked(self):
        primary = Signal("red")
        accent = Signal("blue")
        factory = css_text_template(
            ".btn { color: {{ primary }}; background: {{ accent }}; }",
            {"primary": primary, "accent": accent},
        )

        style = reactive_scoped_style(factory)
        style._bind("multi")

        assert style.dict_computed.value == {".btn": {"color": "red", "background": "blue"}}
        primary.value = "yellow"
        assert style.dict_computed.value == {".btn": {"color": "yellow", "background": "blue"}}
        accent.value = "green"
        assert style.dict_computed.value == {".btn": {"color": "yellow", "background": "green"}}


class TestCssTextTemplateNoInternalComputed:
    def test_factory_is_plain_function_not_computed(self):
        factory = css_text_template(".btn { color: red; }", {})
        assert not isinstance(factory, Computed)
        assert isinstance(factory, types.FunctionType)

    def test_calling_factory_returns_fresh_dict_each_time(self):
        sig = Signal("red")
        factory = css_text_template(".x { color: {{ color }}; }", {"color": sig})

        first = factory()
        second = factory()
        assert first == second
        assert first is not second

    def test_factory_reads_fresh_signal_value_each_call_without_wrapping(self):
        sig = Signal("red")
        factory = css_text_template(".x { color: {{ color }}; }", {"color": sig})

        assert factory() == {".x": {"color": "red"}}
        sig.value = "blue"
        assert factory() == {".x": {"color": "blue"}}

    def test_factory_with_no_signal_dependency_is_pure(self):
        factory = css_text_template(".x { color: red; }", {"unused": "context"})
        assert factory() == {".x": {"color": "red"}}


class TestCssTextTemplateTypeCompatibility:
    def test_assignable_to_reactive_scoped_style_func(self):
        factory = css_text_template(".btn { color: red; }", {})
        typed: ReactiveScopedStyleFunc = factory
        assert typed is factory

    def test_assignable_with_signal_context(self):
        sig = Signal("red")
        factory = css_text_template(".btn { color: {{ c }}; }", {"c": sig})
        typed: ReactiveScopedStyleFunc = factory
        assert typed is factory

    def test_dict_computed_value_via_reactive_scoped_style_returns_dict(self):
        factory = css_text_template(".btn { color: {{ color }}; }", {"color": "blue"})

        style = reactive_scoped_style(factory)
        style._bind("cid-x")

        result = style.dict_computed.value
        assert isinstance(result, dict)
        assert ".btn" in result

    def test_reactive_scoped_style_wrapping_yields_correct_instance(self):
        factory = css_text_template(".btn { color: red; }", {})
        style = reactive_scoped_style(factory)
        assert isinstance(style, ReactiveScopedStyle)


class TestCssTextDedent:
    def test_dedent_applied_to_indented_css(self):
        css = """
            .btn {
                color: red;
            }
        """
        assert css_text(css) == {".btn": {"color": "red"}}

    def test_dedent_applied_to_multi_rule_css(self):
        css = """
            .a {
                color: red;
            }
            .b {
                color: blue;
            }
        """
        assert css_text(css) == {
            ".a": {"color": "red"},
            ".b": {"color": "blue"},
        }

    def test_dedent_preserves_nested_block(self):
        css = """
            .btn {
                color: red;
                :hover {
                    background: blue;
                }
            }
        """
        assert css_text(css) == {
            ".btn": {
                "color": "red",
                ":hover": {"background": "blue"},
            }
        }
