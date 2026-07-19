from __future__ import annotations

import pytest

from webcompy.elements import DomNodeRef
from webcompy.elements.types._element import Element
from webcompy.exception import WebComPyException
from webcompy.signal import Signal
from webcompy.template import render_template
from webcompy.template._cache import clear_cache, get_or_compile
from webcompy.template._parser import parse_template


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_cache()
    yield
    clear_cache()


class TestEndToEnd:
    def test_basic_div_structure(self):
        result = render_template("<div><p>Hello</p></div>", {})
        assert isinstance(result, Element)
        assert result._tag_name == "div"
        assert len(result._children) == 1
        p = result._children[0]
        assert isinstance(p, Element)
        assert p._tag_name == "p"
        assert p._children[0]._text == "Hello"

    def test_with_signal(self):
        sig = Signal("hello")
        result = render_template("<p>{{ value }}</p>", {"value": sig})
        assert result._children[0]._text is sig

    def test_with_dot_notation(self):
        result = render_template(
            "<p>{{ user.name }}</p>",
            {"user": {"name": "Alice"}},
        )
        assert result._children[0]._text == "Alice"


class TestLocalsUsage:
    def test_locals_captures_variables(self):
        name = "Alice"
        age = 30
        result = render_template("<p>{{ name }} is {{ age }}</p>", locals())
        text = "".join(c._text for c in result._children if hasattr(c, "_text"))
        assert "Alice is 30" in text


class TestCompileCache:
    def test_cache_hit_same_string(self):
        call_count = {"n": 0}

        original_parse = parse_template

        def counting_parse(source):
            call_count["n"] += 1
            return original_parse(source)

        from webcompy.template import _cache as cache_mod

        cache_mod._template_cache.clear()
        get_or_compile("<div></div>", parse_fn=counting_parse)
        get_or_compile("<div></div>", parse_fn=counting_parse)
        assert call_count["n"] == 1

    def test_cache_miss_different_strings(self):
        call_count = {"n": 0}

        original_parse = parse_template

        def counting_parse(source):
            call_count["n"] += 1
            return original_parse(source)

        get_or_compile("<div></div>", parse_fn=counting_parse)
        get_or_compile("<span></span>", parse_fn=counting_parse)
        assert call_count["n"] == 2

    def test_render_template_uses_cache(self):
        render_template("<p>x</p>", {})
        render_template("<p>x</p>", {})
        render_template("<p>y</p>", {})
        cached = get_or_compile("<p>x</p>")
        assert cached is get_or_compile("<p>x</p>")

    def test_eviction_when_size_exceeds_max(self):
        from webcompy.template import _cache as cache_mod

        max_size = cache_mod._TEMPLATE_CACHE_MAX_SIZE
        for i in range(max_size + 1):
            get_or_compile(f'<div data-i="{i}"></div>')
        assert len(cache_mod._template_cache) == max_size
        assert '<div data-i="0"></div>' not in cache_mod._template_cache
        assert f'<div data-i="{max_size}"></div>' in cache_mod._template_cache

    def test_lru_access_keeps_entry_alive(self):
        from webcompy.template import _cache as cache_mod

        max_size = cache_mod._TEMPLATE_CACHE_MAX_SIZE
        get_or_compile('<div id="first"></div>')
        for i in range(max_size - 1):
            get_or_compile(f'<div data-i="{i}"></div>')
        assert len(cache_mod._template_cache) == max_size
        get_or_compile('<div id="first"></div>')
        get_or_compile('<div id="newcomer"></div>')
        assert len(cache_mod._template_cache) == max_size
        assert '<div id="first"></div>' in cache_mod._template_cache
        assert '<div data-i="0"></div>' not in cache_mod._template_cache

    def test_eviction_respects_parse_fn_injection(self):
        from webcompy.template import _cache as cache_mod

        call_count = {"n": 0}

        def stub_parse(source):
            call_count["n"] += 1
            return parse_template(source)

        max_size = cache_mod._TEMPLATE_CACHE_MAX_SIZE
        for i in range(max_size + 5):
            get_or_compile(f'<div data-i="{i}"></div>', parse_fn=stub_parse)
        assert call_count["n"] == max_size + 5
        first_again = get_or_compile('<div data-i="0"></div>', parse_fn=stub_parse)
        assert call_count["n"] == max_size + 6
        assert isinstance(first_again[0].tag_name, str)


class TestDedentBehavior:
    def test_indented_triple_quoted(self):
        template = """
            <div>
                <p>{{ name }}</p>
            </div>
        """
        result = render_template(template, {"name": "Alice"})
        assert result._tag_name == "div"
        p = next(c for c in result._children if hasattr(c, "_tag_name"))
        assert p._tag_name == "p"
        assert p._children[0]._text == "Alice"

    def test_different_indentation_same_template(self):
        template_a = """
            <p>{{ name }}</p>
        """
        template_b = """
                <p>{{ name }}</p>
            """
        result_a = render_template(template_a, {"name": "x"})
        result_b = render_template(template_b, {"name": "x"})
        assert result_a._tag_name == "p"
        assert result_b._tag_name == "p"


class TestRootElementValidation:
    def test_single_root_ok(self):
        result = render_template("<div></div>", {})
        assert isinstance(result, Element)

    def test_multiple_roots_raises(self):
        with pytest.raises(
            WebComPyException,
            match="exactly one root element",
        ):
            render_template("<div></div><span></span>", {})

    def test_no_root_raises(self):
        with pytest.raises(
            WebComPyException,
            match="exactly one root element",
        ):
            render_template("", {})

    def test_whitespace_only_around_root_trimmed(self):
        result = render_template("\n   <div></div>\n  ", {})
        assert isinstance(result, Element)
        assert result._tag_name == "div"

    def test_non_whitespace_text_around_root_raises(self):
        with pytest.raises(
            WebComPyException,
            match="exactly one root element",
        ):
            render_template("before<div></div>after", {})

    def test_text_only_no_root_raises(self):
        with pytest.raises(
            WebComPyException,
            match="exactly one root element",
        ):
            render_template("just text", {})


class TestLenientUnknownTags:
    def test_unknown_tag_accepted(self):
        result = render_template("<widget>text</widget>", {})
        assert result._tag_name == "widget"
        assert result._children[0]._text == "text"

    def test_kebab_case_tag(self):
        result = render_template("<my-component>x</my-component>", {})
        assert result._tag_name == "my-component"

    def test_data_attributes(self):
        result = render_template('<div data-testid="x">y</div>', {})
        assert result._attrs["data-testid"] == "x"


class TestRenderNodesShared:
    def test_render_nodes_returns_list(self):
        from webcompy.template import _render_nodes

        nodes = _render_nodes("<div></div><span></span>", {})
        assert len(nodes) == 2

    def test_render_nodes_text_only_returns_string_child(self):
        from webcompy.template import _render_nodes

        nodes = _render_nodes("text only", {})
        assert len(nodes) == 1
        assert nodes[0] == "text only"

    def test_render_nodes_with_whitespace(self):
        from webcompy.template import _render_nodes

        nodes = _render_nodes("  <div></div>  ", {})
        assert len(nodes) == 1


class TestRefIntegration:
    def test_ref_binding_integration(self):
        ref = DomNodeRef()
        result = render_template('<input :ref="my_ref">', {"my_ref": ref})
        assert result._ref is ref
