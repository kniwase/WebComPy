from __future__ import annotations

import pytest

from tests.conftest import FakeDOMNode
from webcompy.elements.types._element import Element
from webcompy.elements.types._text import NewLine, TextElement
from webcompy.signal import Computed, Signal, SignalBase
from webcompy.template._binder import (
    bind_element,
    classify_attrs,
)
from webcompy.template._holes import resolve_var
from webcompy.template._parser import parse_template


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _mount_in_parent(result):
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._event_handlers_added = {}
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    result._parent = parent
    result._node_idx = 0
    return parent


class TestTextInterpolation:
    def test_signal_in_text(self):
        sig = Signal("hello")
        roots = parse_template("<p>{{ value }}</p>")
        result = bind_element(roots[0], {"value": sig})
        assert isinstance(result, Element)
        assert len(result._children) == 1
        text_el = result._children[0]
        assert isinstance(text_el, TextElement)
        assert text_el._text is sig

    def test_string_in_text(self):
        roots = parse_template("<p>{{ value }}</p>")
        result = bind_element(roots[0], {"value": "hello"})
        assert isinstance(result._children[0], TextElement)
        assert result._children[0]._text == "hello"

    def test_int_in_text(self):
        roots = parse_template("<p>{{ value }}</p>")
        result = bind_element(roots[0], {"value": 42})
        assert isinstance(result._children[0], TextElement)
        assert result._children[0]._text == "42"

    def test_none_value_omitted(self):
        roots = parse_template("<p>before{{ value }}after</p>")
        result = bind_element(roots[0], {"value": None})
        assert len(result._children) == 2
        assert result._children[0]._text == "before"
        assert result._children[1]._text == "after"

    def test_element_as_variable(self):
        child = Element("span", {}, [], None, ["x"])
        roots = parse_template("<div>{{ card }}</div>")
        result = bind_element(roots[0], {"card": child})
        assert isinstance(result, Element)
        assert len(result._children) == 1
        assert result._children[0] is child

    def test_mixed_literal_and_signal_text(self):
        sig = Signal("world")
        roots = parse_template("<p>Hello {{ name }}!</p>")
        result = bind_element(roots[0], {"name": sig})
        assert len(result._children) == 3
        assert result._children[0]._text == "Hello "
        assert result._children[1]._text is sig
        assert result._children[2]._text == "!"


class TestDotNotation:
    def test_dict_access(self):
        roots = parse_template("<p>{{ user.name }}</p>")
        result = bind_element(roots[0], {"user": {"name": "Alice"}})
        assert isinstance(result._children[0], TextElement)
        assert result._children[0]._text == "Alice"

    def test_object_attribute_access(self):
        class User:
            name = "Bob"

        roots = parse_template("<p>{{ user.name }}</p>")
        result = bind_element(roots[0], {"user": User()})
        assert result._children[0]._text == "Bob"

    def test_chained_access(self):
        roots = parse_template("<p>{{ outer.inner.value }}</p>")
        result = bind_element(roots[0], {"outer": {"inner": {"value": 100}}})
        assert result._children[0]._text == "100"


class TestAttributeEvaluation:
    def test_none_in_attr_renders_empty(self):
        roots = parse_template('<p class="{{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": None})
        assert result._attrs["class"] == ""

    def test_signal_none_in_attr_renders_empty(self):
        sig = Signal(None)
        roots = parse_template('<p class="{{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": sig})
        attr_value = result._attrs["class"]
        assert isinstance(attr_value, Computed)
        assert attr_value.value == ""

    def test_mixed_literal_and_none_in_attr(self):
        roots = parse_template('<p class="card {{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": None})
        assert result._attrs["class"] == "card "

    def test_mixed_literal_and_signal_none_in_attr(self):
        sig = Signal(None)
        roots = parse_template('<p class="card {{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": sig})
        attr_value = result._attrs["class"]
        assert isinstance(attr_value, Computed)
        assert attr_value.value == "card "

    def test_single_signal_creates_computed(self):
        sig = Signal("active")
        roots = parse_template('<p class="{{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": sig})
        attr_value = result._attrs["class"]
        assert isinstance(attr_value, Computed)
        assert attr_value.value == "active"

    def test_mixed_literal_and_signal_creates_computed(self):
        sig = Signal("active")
        roots = parse_template('<p class="card {{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": sig})
        attr_value = result._attrs["class"]
        assert isinstance(attr_value, Computed)
        assert attr_value.value == "card active"

    def test_multiple_signals_creates_computed(self):
        a = Signal("foo")
        b = Signal("bar")
        roots = parse_template('<p data-label="{{ a }} {{ b }}"></p>')
        result = bind_element(roots[0], {"a": a, "b": b})
        attr_value = result._attrs["data-label"]
        assert isinstance(attr_value, Computed)
        assert attr_value.value == "foo bar"

    def test_static_no_signal_returns_plain_string(self):
        roots = parse_template('<p class="{{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": "static-string"})
        attr_value = result._attrs["class"]
        assert attr_value == "static-string"
        assert not isinstance(attr_value, SignalBase)

    def test_int_static(self):
        roots = parse_template('<p data-index="{{ idx }}"></p>')
        result = bind_element(roots[0], {"idx": 42})
        assert result._attrs["data-index"] == "42"

    def test_mixed_literal_and_non_signal(self):
        roots = parse_template('<p class="card {{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": "active"})
        assert result._attrs["class"] == "card active"

    def test_boolean_attr(self):
        roots = parse_template("<input disabled>")
        result = bind_element(roots[0], {})
        assert result._attrs["disabled"] is True

    def test_boolean_attr_with_explicit_value(self):
        roots = parse_template('<input disabled="disabled">')
        result = bind_element(roots[0], {})
        assert result._attrs["disabled"] == "disabled"

    def test_computed_updates_on_signal_change(self, fake_browser_full):
        sig = Signal("a")
        roots = parse_template('<p class="{{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": sig})
        _mount_in_parent(result)
        result._init_node()
        node = result._get_node()
        assert node.getAttribute("class") == "a"
        sig.value = "b"
        assert node.getAttribute("class") == "b"

    def test_computed_cleanup_on_element_removal(self, fake_browser_full):
        sig = Signal("a")
        roots = parse_template('<p class="{{ cls }}"></p>')
        result = bind_element(roots[0], {"cls": sig})
        attr_value = result._attrs["class"]
        assert isinstance(attr_value, Computed)
        _mount_in_parent(result)
        result._init_node()
        callback_nodes_before = list(result._callback_nodes)
        assert len(callback_nodes_before) > 0
        for node in callback_nodes_before:
            assert node.producers is not None
        result._remove_element()
        for node in callback_nodes_before:
            assert node.producers is None


class TestEventHandlerBinding:
    def test_click_handler(self):
        def handler(_):
            pass

        roots = parse_template('<button @click="on_click">Btn</button>')
        result = bind_element(roots[0], {"on_click": handler})
        assert result._event_handlers["click"] is handler

    def test_multiple_handlers(self):
        def h1(_):
            pass

        def h2(_):
            pass

        roots = parse_template('<button @click="h1" @mouseover="h2">Btn</button>')
        result = bind_element(roots[0], {"h1": h1, "h2": h2})
        assert result._event_handlers["click"] is h1
        assert result._event_handlers["mouseover"] is h2

    def test_missing_event_handler_raises_keyerror(self):
        roots = parse_template('<button @click="missing">Btn</button>')
        with pytest.raises(KeyError, match="missing"):
            bind_element(roots[0], {})


class TestDomNodeRefBinding:
    def test_ref_binding(self):
        from webcompy.elements import DomNodeRef

        ref = DomNodeRef()
        roots = parse_template('<input :ref="my_ref">')
        result = bind_element(roots[0], {"my_ref": ref})
        assert result._ref is ref

    def test_ref_missing_raises(self):
        roots = parse_template('<input :ref="nonexistent">')
        with pytest.raises(KeyError):
            bind_element(roots[0], {})


class TestEventRefAttrValidation:
    def test_event_attr_with_hole_raises(self):
        from webcompy.exception import WebComPyException

        roots = parse_template('<button @click="{{ h }}">Btn</button>')
        with pytest.raises(WebComPyException, match=r"@click"):
            bind_element(roots[0], {"h": lambda _: None})

    def test_ref_attr_with_hole_raises(self):
        from webcompy.elements import DomNodeRef
        from webcompy.exception import WebComPyException

        roots = parse_template('<input :ref="{{ r }}">')
        with pytest.raises(WebComPyException, match=r":ref"):
            bind_element(roots[0], {"r": DomNodeRef()})

    def test_non_callable_event_handler_raises(self):
        from webcompy.exception import WebComPyException

        roots = parse_template('<button @click="x">Btn</button>')
        with pytest.raises(WebComPyException, match="not callable"):
            bind_element(roots[0], {"x": 42})


class TestMissingVariable:
    def test_missing_variable_raises_with_available_names(self):
        roots = parse_template("<p>{{ missing }}</p>")
        with pytest.raises(KeyError, match="missing"):
            bind_element(roots[0], {"present": "x"})

    def test_missing_attr_variable_raises(self):
        roots = parse_template('<p class="{{ cls }}"></p>')
        with pytest.raises(KeyError, match="cls"):
            bind_element(roots[0], {})


class TestBrSpecialCasing:
    def test_br_becomes_newline(self):
        roots = parse_template("<div><br></div>")
        result = bind_element(roots[0], {})
        assert len(result._children) == 1
        assert isinstance(result._children[0], NewLine)

    def test_self_closing_br(self):
        roots = parse_template("<div><br /></div>")
        result = bind_element(roots[0], {})
        assert isinstance(result._children[0], NewLine)


class TestResolveVarDirect:
    def test_resolve_var_dict_missing_raises(self):
        with pytest.raises(KeyError, match="missing"):
            resolve_var("missing", {"present": "x"})


class TestClassifyAttrs:
    def test_event_ref_and_regular_attrs(self):
        def handler(_):
            pass

        from webcompy.elements import DomNodeRef

        ref = DomNodeRef()
        roots = parse_template('<input id="myid" @click="on_click" :ref="my_ref">')
        events, ref_out, regular = classify_attrs(
            roots[0].attrs,
            {
                "on_click": handler,
                "my_ref": ref,
            },
        )
        assert "click" in events
        assert events["click"] is handler
        assert ref_out is ref
        assert len(regular) == 1
        assert regular[0].name == "id"
