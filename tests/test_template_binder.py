from __future__ import annotations

import pytest

from tests.conftest import FakeDOMNode
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import NewLine, TextElement
from webcompy.exception import WebComPyException
from webcompy.signal import Computed, ReactiveDict, ReactiveList, Signal, SignalBase
from webcompy.template._ast import AttrSpec
from webcompy.template._binder import (
    bind_element,
    classify_attrs,
)
from webcompy.template._holes import LiteralText, resolve_var
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


class TestBindAttrBinding:
    def test_bind_binding(self):
        sig = Signal("hi")
        roots = parse_template('<input :bind="text">')
        result = bind_element(roots[0], {"text": sig})
        assert isinstance(result, Element)
        assert result._attrs.get("value") is sig
        assert ":bind" not in result._attrs
        assert "input" in result._event_handlers

    def test_bind_on_textarea(self):
        sig = Signal("hi")
        roots = parse_template('<textarea :bind="text"></textarea>')
        result = bind_element(roots[0], {"text": sig})
        assert "value" not in result._attrs
        assert len(result._children) == 1
        assert isinstance(result._children[0], TextElement)
        assert result._children[0]._text is sig
        assert "input" in result._event_handlers

    def test_bind_non_signal_raises_naming_variable_and_type(self):
        roots = parse_template('<input :bind="text">')
        with pytest.raises(WebComPyException, match=r"text.*str"):
            bind_element(roots[0], {"text": "literal"})

    def test_bind_computed_raises(self):
        roots = parse_template('<input :bind="text">')
        with pytest.raises(WebComPyException, match="writable Signal"):
            bind_element(roots[0], {"text": Computed(lambda: "x")})

    def test_bind_hole_raises(self):
        sig = Signal("hi")
        roots = parse_template('<input :bind="{{ text }}">')
        with pytest.raises(WebComPyException, match=r":bind"):
            bind_element(roots[0], {"text": sig})

    def test_other_colon_attr_rejected_with_updated_message(self):
        roots = parse_template('<div :class="cls"></div>')
        with pytest.raises(WebComPyException, match=r"':ref' and ':bind'"):
            bind_element(roots[0], {"cls": "x"})


class TestRadioTemplateValueComparison:
    def test_template_string_value_never_matches_int_signal(self):
        choice = Signal(1)
        roots = parse_template('<input type="radio" value="1" :bind="choice">')
        result = bind_element(roots[0], {"choice": choice})
        checked = result._attrs["checked"]
        assert isinstance(checked, Computed)
        assert checked.value is False

    def test_template_string_value_matches_str_signal(self):
        choice = Signal("1")
        roots = parse_template('<input type="radio" value="1" :bind="choice">')
        result = bind_element(roots[0], {"choice": choice})
        checked = result._attrs["checked"]
        assert isinstance(checked, Computed)
        assert checked.value is True

    def test_element_api_preserves_non_string_value(self):
        choice = Signal(1)
        result = Element("input", {"type": "radio", "value": 1, ":bind": choice}, {}, None, None)
        checked = result._attrs["checked"]
        assert isinstance(checked, Computed)
        assert checked.value is True


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
        events, ref_out, _bind_out, regular = classify_attrs(
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


class TestIfBindingReactive:
    def test_reactive_if_with_signal_condition(self):
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        sig = Signal(True)
        roots = parse_template("{% if show %}A{% endif %}")
        assert len(roots) == 1
        from webcompy.template._ast import IfNode

        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"show": sig})
        assert len(result) == 1
        assert isinstance(result[0], SwitchElement)
        sw = result[0]
        assert len(sw._cases) == 1
        assert sw._cases[0][0] is sig

    def test_reactive_if_with_dot_notation(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        class Item:
            def __init__(self):
                self.visible = Signal(True)

        item = Item()
        roots = parse_template("{% if item.visible %}A{% endif %}")
        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"item": item})
        assert len(result) == 1
        assert isinstance(result[0], SwitchElement)
        assert result[0]._cases[0][0] is item.visible

    def test_multi_element_branch_uses_fragment(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        sig = Signal(True)
        roots = parse_template("{% if show %}<p>a</p><p>b</p>{% endif %}")
        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"show": sig})
        assert len(result) == 1
        assert isinstance(result[0], SwitchElement)
        sw = result[0]
        generated = sw._select_generator()[1]()
        assert isinstance(generated, FragmentElement)
        assert len(generated._pending_children) == 2


class TestIfBindingStatic:
    def test_static_if_truthy_returns_children(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% if flag %}A{% endif %}")
        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"flag": True})
        assert result == ["A"]

    def test_static_if_falsy_returns_empty(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% if flag %}A{% endif %}")
        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"flag": False})
        assert result == []

    def test_static_if_none_returns_empty(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% if flag %}A{% endif %}")
        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"flag": None})
        assert result == []

    def test_static_if_elif_else_first_truthy(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% if a %}A{% elif b %}B{% else %}C{% endif %}")
        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"a": True, "b": False})
        assert result == ["A"]

    def test_static_if_elif_else_second_truthy(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% if a %}A{% elif b %}B{% else %}C{% endif %}")
        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"a": False, "b": True})
        assert result == ["B"]

    def test_static_if_elif_else_falls_through_to_else(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% if a %}A{% elif b %}B{% else %}C{% endif %}")
        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"a": False, "b": False})
        assert result == ["C"]

    def test_static_if_multi_child_branch_appends(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("<div>{% if flag %}<p>a</p><p>b</p>{% endif %}</div>")
        div = roots[0]
        if_node = div.children[0]
        assert isinstance(if_node, IfNode)
        result = bind_children([if_node], {"flag": True})
        assert len(result) == 2
        assert all(isinstance(e, Element) for e in result)


class TestIfMixedConditions:
    def test_mixed_signal_and_static_triggers_reactive(self):
        from webcompy.template._ast import IfNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        sig = Signal(False)
        roots = parse_template("{% if signal_a %}A{% elif plain_bool %}B{% endif %}")
        assert isinstance(roots[0], IfNode)
        result = bind_children(roots, {"signal_a": sig, "plain_bool": True})
        assert len(result) == 1
        assert isinstance(result[0], SwitchElement)


class TestForBindingReactive:
    def test_reactive_for_with_reactive_list_single_child(self):
        from webcompy.elements.types._repeat import RepeatElement
        from webcompy.template._ast import ForNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        rl = ReactiveList(["a", "b", "c"])
        roots = parse_template("{% for item in items %}<p>{{ item }}</p>{% endfor %}")
        assert isinstance(roots[0], ForNode)
        result = bind_children(roots, {"items": rl})
        assert len(result) == 1
        assert isinstance(result[0], RepeatElement)

    def test_reactive_for_with_multiple_children_uses_fragment(self):
        from webcompy.elements.types._repeat import RepeatElement
        from webcompy.template._ast import ForNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        rl = ReactiveList(["a", "b"])
        roots = parse_template("{% for item in items %}<p>a</p><p>b</p>{% endfor %}")
        assert isinstance(roots[0], ForNode)
        result = bind_children(roots, {"items": rl})
        assert len(result) == 1
        rep = result[0]
        assert isinstance(rep, RepeatElement)
        rep._parent = _make_parent_stub()
        rep._on_set_parent()
        assert len(rep._children) == 2
        for child in rep._children:
            assert isinstance(child, FragmentElement)
            assert len(child._children) == 2

    def test_reactive_for_with_reactive_dict(self):
        from webcompy.elements.types._repeat import RepeatElement
        from webcompy.template._ast import ForNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        rd = ReactiveDict({"x": 1, "y": 2})
        roots = parse_template("{% for value in d %}<p>{{ value }}</p>{% endfor %}")
        assert isinstance(roots[0], ForNode)
        result = bind_children(roots, {"d": rd})
        assert len(result) == 1
        assert isinstance(result[0], RepeatElement)

    def test_reactive_for_with_dict_unpacking(self):
        from webcompy.elements.types._repeat import RepeatElement
        from webcompy.template._ast import ForNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        rd = ReactiveDict({"a": 1, "b": 2})
        roots = parse_template("{% for key, value in d %}<p>{{ key }}={{ value }}</p>{% endfor %}")
        assert isinstance(roots[0], ForNode)
        result = bind_children(roots, {"d": rd})
        assert len(result) == 1
        rep = result[0]
        assert isinstance(rep, RepeatElement)
        rep._parent = _make_parent_stub()
        rep._on_set_parent()
        assert len(rep._children) == 2


class TestForBindingStatic:
    def test_static_for_with_plain_list_single_child(self):
        from webcompy.template._ast import ForNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% for item in items %}<p>x</p>{% endfor %}")
        assert isinstance(roots[0], ForNode)
        result = bind_children(roots, {"items": [1, 2, 3]})
        assert len(result) == 3
        assert all(isinstance(e, Element) and e._tag_name == "p" for e in result)

    def test_static_for_with_multiple_children_no_fragment(self):
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% for item in items %}<a>a</a><b>b</b>{% endfor %}")
        result = bind_children(roots, {"items": [1, 2]})
        assert len(result) == 4
        assert not any(isinstance(r, FragmentElement) for r in result)


class TestLoopVariableScoping:
    def test_loop_var_visible_in_body(self):
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% for item in items %}<p>{{ item }}</p>{% endfor %}")
        result = bind_children(roots, {"items": ["x", "y"]})
        assert len(result) == 2
        for el in result:
            assert isinstance(el, Element)
            children = el._children
            assert len(children) == 1
            assert isinstance(children[0], TextElement)
            assert children[0]._text in ("x", "y")

    def test_dot_notation_in_for_iterable(self):
        from webcompy.template._ast import ForNode
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        class User:
            def __init__(self):
                self.posts = ["p1", "p2"]

        roots = parse_template("{% for post in user.posts %}<p>x</p>{% endfor %}")
        assert isinstance(roots[0], ForNode)
        result = bind_children(roots, {"user": User()})
        assert len(result) == 2


class TestDictKeyValueMapping:
    def test_reactive_dict_two_var_uses_two_arg_template(self):
        from webcompy.elements.types._repeat import RepeatElement
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        rd = ReactiveDict({"a": 1, "b": 2})
        roots = parse_template("{% for key, value in d %}<p>k:{{ key }} v:{{ value }}</p>{% endfor %}")
        result = bind_children(roots, {"d": rd})
        rep = result[0]
        assert isinstance(rep, RepeatElement)
        assert rep._two_arg_template is not None
        rep._parent = _make_parent_stub()
        rep._on_set_parent()
        assert len(rep._children) == 2

    def test_static_dict_two_var_binds_both(self):
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("{% for key, value in d %}<p>{{ key }}={{ value }}</p>{% endfor %}")
        result = bind_children(roots, {"d": {"a": 1, "b": 2}})
        assert len(result) == 2
        for el in result:
            assert isinstance(el, Element)
            joined = "".join(c._text if isinstance(c, TextElement) else str(c) for c in el._children)
            assert joined in ("a=1", "b=2")


def _make_parent_stub():
    from tests.conftest import FakeDOMNode
    from webcompy.elements.types._element import Element

    class FakeRootElement(Element):
        _get_belonging_component = lambda self: ""
        _get_belonging_components = lambda self: ()

    parent = FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


class TestClassifyAttrsValidation:
    def test_non_ref_colon_attribute_raises(self):
        with pytest.raises(WebComPyException) as exc_info:
            classify_attrs([AttrSpec(name=":class", value=[LiteralText("cls")])], ctx={})
        msg = str(exc_info.value)
        assert ":class" in msg
        assert "{{" in msg
        assert "class=" in msg

    def test_ref_binding_type_validation(self):
        from webcompy.elements.types._refference import DomNodeRef

        ref = DomNodeRef()
        attr = AttrSpec(name=":ref", value=[LiteralText("r")])
        _events, got_ref, _bind_out, _ = classify_attrs([attr], ctx={"r": ref})
        assert got_ref is ref

    def test_ref_with_non_DomNodeRef_raises(self):
        attr = AttrSpec(name=":ref", value=[LiteralText("r")])
        with pytest.raises(WebComPyException) as exc_info:
            classify_attrs([attr], ctx={"r": "not-a-ref"})
        msg = str(exc_info.value)
        assert "r" in msg
        assert "str" in msg
        assert "DomNodeRef" in msg

    def test_event_modifier_rejected(self):
        attr = AttrSpec(name="@click.stop", value=[LiteralText("handler")])

        def handler(_event):
            pass

        with pytest.raises(WebComPyException) as exc_info:
            classify_attrs([attr], ctx={"handler": handler})
        msg = str(exc_info.value)
        assert "@click.stop" in msg
        assert "modifier" in msg.lower() or "modifiers" in msg.lower()

    def test_event_without_modifier_still_works(self):
        def handler(_event):
            pass

        attr = AttrSpec(name="@click", value=[LiteralText("handler")])
        events, _, _, _ = classify_attrs([attr], ctx={"handler": handler})
        assert "click" in events


class TestBindIfValidation:
    def test_if_expression_falsy(self):
        roots = parse_template("{% if a > b %}yes{% endif %}")
        from webcompy.template._binder import bind_children

        result = bind_children(roots, {"a": 1, "b": 2})
        # a=1, b=2 → a > b is False → no children
        assert len(result) == 0

    def test_if_expression_truthy(self):
        roots = parse_template("{% if a > b %}yes{% endif %}")
        from webcompy.template._binder import bind_children

        result = bind_children(roots, {"a": 5, "b": 2})
        # a=5, b=2 → a > b is True → body rendered
        assert len(result) >= 1

    def test_if_valid_path_works(self):
        roots = parse_template("{% if flag %}yes{% endif %}")
        from webcompy.template._binder import bind_children

        result = bind_children(roots, {"flag": True})
        assert len(result) == 1


class TestBindForValidation:
    def test_for_non_iterable_int_raises(self):
        roots = parse_template("{% for x in items %}<p>{{ x }}</p>{% endfor %}")
        from webcompy.template._binder import bind_children

        with pytest.raises(WebComPyException) as exc_info:
            bind_children(roots, {"items": 5})
        msg = str(exc_info.value)
        assert "items" in msg
        assert "int" in msg

    def test_for_non_iterable_none_raises(self):
        roots = parse_template("{% for x in items %}<p>{{ x }}</p>{% endfor %}")
        from webcompy.template._binder import bind_children

        with pytest.raises(WebComPyException) as exc_info:
            bind_children(roots, {"items": None})
        msg = str(exc_info.value)
        assert "items" in msg
        assert "NoneType" in msg

    def test_for_string_iterable_works(self):
        roots = parse_template("{% for c in s %}<p>{{ c }}</p>{% endfor %}")
        from webcompy.template._binder import bind_children

        result = bind_children(roots, {"s": "ab"})
        assert len(result) == 2

    def test_for_list_iterable_works(self):
        roots = parse_template("{% for x in items %}<p>{{ x }}</p>{% endfor %}")
        from webcompy.template._binder import bind_children

        result = bind_children(roots, {"items": [1, 2, 3]})
        assert len(result) == 3

    def test_for_invalid_path_raises(self):
        roots = parse_template("{% for x in items[0] %}<p>{{ x }}</p>{% endfor %}")
        from webcompy.template._binder import bind_children

        with pytest.raises(WebComPyException):
            bind_children(roots, {"items": [1, 2, 3]})


class TestEmptyStringAttribute:
    def test_alt_empty_string_renders_as_empty(self):
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template('<img alt="">')
        result = bind_children(roots, {})
        assert isinstance(result[0], Element)
        assert result[0]._attrs.get("alt") == ""

    def test_disabled_empty_string_renders_as_empty(self):
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template('<input disabled="">')
        result = bind_children(roots, {})
        assert isinstance(result[0], Element)
        assert result[0]._attrs.get("disabled") == ""

    def test_disabled_boolean_renders_as_true(self):
        from webcompy.template._binder import bind_children
        from webcompy.template._parser import parse_template

        roots = parse_template("<input disabled>")
        result = bind_children(roots, {})
        assert isinstance(result[0], Element)
        assert result[0]._attrs.get("disabled") is True
