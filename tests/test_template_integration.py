from __future__ import annotations

import pytest

from webcompy.elements import DomNodeRef
from webcompy.elements.types._element import Element
from webcompy.exception import WebComPyException
from webcompy.signal import ReactiveList, Signal
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
        sources_in_cache = {key[0] for key in cache_mod._template_cache}
        assert '<div data-i="0"></div>' not in sources_in_cache
        assert f'<div data-i="{max_size}"></div>' in sources_in_cache

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
        sources_in_cache = {key[0] for key in cache_mod._template_cache}
        assert '<div id="first"></div>' in sources_in_cache
        assert '<div data-i="0"></div>' not in sources_in_cache

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

    def test_kebab_case_tag_raises_when_component_missing(self):
        with pytest.raises(WebComPyException, match="MyComponent"):
            render_template("<my-component>x</my-component>", {})

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


class TestIfIntegration:
    def test_render_template_with_reactive_if(self):
        from webcompy.elements.types._switch import SwitchElement

        sig = Signal(True)
        result = render_template(
            "<div>{% if show %}A{% endif %}</div>",
            {"show": sig},
        )
        assert isinstance(result, Element)
        assert len(result._children) == 1
        assert isinstance(result._children[0], SwitchElement)

    def test_render_template_with_static_if(self):
        result = render_template(
            "<div>{% if flag %}A{% endif %}</div>",
            {"flag": True},
        )
        assert isinstance(result, Element)
        assert len(result._children) == 1
        text = result._children[0]
        if hasattr(text, "_text"):
            assert text._text == "A"
        else:
            assert text == "A"

    def test_render_template_with_static_if_falsy(self):
        result = render_template(
            "<div>{% if flag %}A{% endif %}</div>",
            {"flag": False},
        )
        assert isinstance(result, Element)
        assert result._children == []

    def test_render_template_with_if_else(self):
        result = render_template(
            "<div>{% if flag %}A{% else %}B{% endif %}</div>",
            {"flag": False},
        )
        assert isinstance(result, Element)
        first = result._children[0]
        rendered = first._text if hasattr(first, "_text") else first
        assert rendered == "B"


class TestForIntegration:
    def test_render_template_with_static_for(self):
        result = render_template(
            "<div>{% for item in items %}<p>{{ item }}</p>{% endfor %}</div>",
            {"items": [1, 2, 3]},
        )
        assert isinstance(result, Element)
        p_count = sum(1 for c in result._children if isinstance(c, Element) and c._tag_name == "p")
        assert p_count == 3

    def test_render_template_with_reactive_for(self):
        from webcompy.elements.types._repeat import RepeatElement

        rl = ReactiveList(["a", "b"])
        result = render_template(
            "<div>{% for item in items %}<p>{{ item }}</p>{% endfor %}</div>",
            {"items": rl},
        )
        assert isinstance(result, Element)
        assert any(isinstance(c, RepeatElement) for c in result._children)


class TestNestedControlFlowIntegration:
    def test_for_containing_if(self):
        items_with_flag = [
            {"name": "a", "visible": True},
            {"name": "b", "visible": False},
            {"name": "c", "visible": True},
        ]
        result = render_template(
            "<div>{% for item in items %}{% if item.visible %}<p>{{ item.name }}</p>{% endif %}{% endfor %}</div>",
            {"items": items_with_flag},
        )
        assert isinstance(result, Element)
        p_children = [c for c in result._children if isinstance(c, Element) and c._tag_name == "p"]
        assert len(p_children) == 2
        rendered = [c._children[0]._text if hasattr(c._children[0], "_text") else c._children[0] for c in p_children]
        assert "a" in rendered
        assert "c" in rendered

    def test_if_containing_for(self):
        result = render_template(
            "<div>{% if show %}<ul>{% for x in xs %}<li>x</li>{% endfor %}</ul>{% endif %}</div>",
            {"show": True, "xs": [1, 2, 3]},
        )
        assert isinstance(result, Element)
        ul = next((c for c in result._children if isinstance(c, Element) and c._tag_name == "ul"), None)
        assert ul is not None
        li_count = sum(1 for c in ul._children if isinstance(c, Element) and c._tag_name == "li")
        assert li_count == 3


class TestMultiElementWithFragmentInSwitch:
    def test_multi_element_if_branch_uses_fragment(self):
        from webcompy.elements.types._fragment import FragmentElement
        from webcompy.elements.types._switch import SwitchElement

        sig = Signal(True)
        result = render_template(
            "<div>{% if show %}<p>a</p><p>b</p>{% endif %}</div>",
            {"show": sig},
        )
        assert isinstance(result, Element)
        assert isinstance(result._children[0], SwitchElement)
        sw = result._children[0]
        generated = sw._select_generator()[1]()
        assert isinstance(generated, FragmentElement)


class TestMultiElementWithFragmentInRepeat:
    def test_multi_element_for_body_uses_fragment(self):
        from webcompy.elements.types._fragment import FragmentElement
        from webcompy.elements.types._repeat import RepeatElement

        rl = ReactiveList(["a"])
        result = render_template(
            "<div>{% for item in items %}<a>{{ item }}</a><b>x</b>{% endfor %}</div>",
            {"items": rl},
        )
        assert isinstance(result, Element)
        rep = next(c for c in result._children if isinstance(c, RepeatElement))
        rep._parent = result
        rep._on_set_parent()
        assert len(rep._children) == 1
        assert isinstance(rep._children[0], FragmentElement)


class TestSwitchTruthinessSemantics:
    def test_signal_true_switches_to_truthy(self):
        from webcompy.elements.types._switch import SwitchElement

        cond = Signal(True)
        result = render_template(
            "<div>{% if cond %}A{% else %}B{% endif %}</div>",
            {"cond": cond},
        )
        assert isinstance(result, Element)
        sw = result._children[0]
        assert isinstance(sw, SwitchElement)
        idx, _ = sw._select_generator()
        assert idx == 0

    def test_signal_false_switches_to_else(self):

        cond = Signal(False)
        result = render_template(
            "<div>{% if cond %}A{% else %}B{% endif %}</div>",
            {"cond": cond},
        )
        assert isinstance(result, Element)
        sw = result._children[0]
        idx, _ = sw._select_generator()
        assert idx == -1

    def test_signal_with_falsy_string(self):

        cond = Signal("")
        result = render_template(
            "<div>{% if cond %}A{% else %}B{% endif %}</div>",
            {"cond": cond},
        )
        assert isinstance(result, Element)
        sw = result._children[0]
        idx, _ = sw._select_generator()
        assert idx == -1


class TestComponentTagEndToEnd:
    """Integration: ``render_template`` produces a rendered Component subtree."""

    def test_render_template_resolves_kebab_component(self):
        from webcompy.components._generator import (
            ComponentGenerator,
            ComponentStore,
        )
        from webcompy.elements.types._text import TextElement

        captured: dict[str, object] = {}

        def setup(ctx):
            captured["title"] = ctx.props.get("title")
            return Element("section", {}, [], None, [TextElement("ok")])

        store = ComponentStore()
        store.add_component("UserCard", ComponentGenerator("UserCard", setup))

        with _store_di_scope(store):
            result = render_template("<div><user-card title='Hi' /></div>")
        assert captured["title"] == "Hi"
        assert isinstance(result, Element)
        assert result._tag_name == "div"
        # The first child of the wrapper div is the rendered UserCard section.
        # The binder yields a Component which has been rendered to its template
        # Element; both share ElementBase so we assert behaviorally.
        first_child = result._children[0]
        assert first_child._tag_name == "section"


def _store_di_scope(store):
    from contextlib import contextmanager

    from webcompy.components._component import HeadPropsStore
    from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
    from webcompy.di._scope import DIScope, _active_di_scope

    @contextmanager
    def ctx():
        head_props = HeadPropsStore()
        parent_scope = _active_di_scope.get(None)
        if parent_scope is not None and getattr(parent_scope, "_disposed", False):
            parent_scope = None
        scope = parent_scope.create_child() if parent_scope is not None else DIScope()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.provide(_HEAD_PROPS_KEY, head_props)
        token = _active_di_scope.set(scope)
        try:
            yield scope
        finally:
            _active_di_scope.reset(token)
            scope.dispose()

    return ctx()


class TestNestedComponentTags:
    def test_parent_template_contains_child_component_tag(self):
        from webcompy.components._generator import (
            ComponentGenerator,
            ComponentStore,
        )
        from webcompy.elements.types._text import TextElement

        def inner(ctx):
            return Element(
                "span",
                {},
                [],
                None,
                [TextElement(ctx.props.get("label", ""))],
            )

        store = ComponentStore()
        store.add_component("InnerCard", ComponentGenerator("InnerCard", inner))

        with _store_di_scope(store):
            result = render_template(
                "<div><inner-card label='hi' /></div>",
            )
        assert isinstance(result, Element)
        assert result._tag_name == "div"
        inner = result._children[0]
        assert inner._tag_name == "span"
        assert inner._children[0]._text == "hi"


class TestReactivePropUpdates:
    def test_signal_prop_changes_after_initial_render(self):
        from webcompy.components._generator import (
            ComponentGenerator,
            ComponentStore,
        )
        from webcompy.elements.types._text import TextElement

        def renderable(ctx):
            value = ctx.props.get("value")
            text = value.value if hasattr(value, "value") else str(value)
            return Element("p", {}, [], None, [TextElement(text)])

        store = ComponentStore()
        store.add_component("ReactiveCount", ComponentGenerator("ReactiveCount", renderable))

        sig = Signal("a")
        with _store_di_scope(store):
            first = render_template("<div><reactive-count :value='v' /></div>", {"v": sig})
        assert isinstance(first, Element)
        # The component tag renders to its template <p>; navigate into that.
        assert first._children[0]._tag_name == "p"
        assert first._children[0]._children[0]._text == "a"

        sig.value = "b"
        with _store_di_scope(store):
            second = render_template("<div><reactive-count :value='v' /></div>", {"v": sig})
        assert isinstance(second, Element)
        assert second._children[0]._children[0]._text == "b"
