from typing import Protocol
from unittest.mock import MagicMock

from webcompy.elements._dom_objs import DOMEvent, DOMNode
from webcompy.elements.generators import (
    break_line,
    create_element,
    event,
    noderef,
    repeat,
    switch,
    text,
)
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements.types._text import TextElement
from webcompy.exception import WebComPyException
from webcompy.signal import ReactiveList, Signal


class TestTypeAliases:
    def test_dom_node_is_protocol(self):
        assert issubclass(DOMNode, Protocol)

    def test_dom_event_is_protocol(self):
        assert issubclass(DOMEvent, Protocol)


class TestDomNodeRef:
    def test_initial_node_is_none(self):
        ref = DomNodeRef()
        assert ref._node is None

    def test_element_raises_when_not_initialized(self):
        ref = DomNodeRef()
        try:
            _ = ref.element
            raise AssertionError("Should have raised")
        except WebComPyException:
            pass

    def test_init_node_sets_node(self):
        ref = DomNodeRef()

        class FakeNode:
            pass

        node = FakeNode()
        ref.__init_node__(node)
        assert ref._node is node

    def test_reset_node_clears(self):
        ref = DomNodeRef()

        class FakeNode:
            pass

        ref.__init_node__(FakeNode())
        ref.__reset_node__()
        assert ref._node is None


def _make_parent():
    parent = MagicMock()
    parent._get_belonging_component.return_value = ""
    return parent


class TestGenerators:
    def test_event_wraps_with_at_prefix(self):
        ev = event("click")
        assert ev == "@click"

    def test_noderef_is_ref_key(self):
        assert noderef == ":ref"

    def test_create_element_separates_attrs(self):
        ref = DomNodeRef()
        el = create_element(
            "div",
            {"class": "test", "id": "x", "@click": lambda: None, ":ref": ref},
        )
        assert el._attrs == {"class": "test", "id": "x"}
        assert "click" in el._event_handlers
        assert el._ref is ref

    def test_create_element_no_events(self):
        el = create_element("div", {"class": "test"})
        assert el._attrs == {"class": "test"}
        assert el._event_handlers == {}

    def test_text_creates_multiline_text_element(self):
        t = text("hello")
        assert hasattr(t, "_sequence")

    def test_text_creates_plain_text_element(self):
        t = text("hello", enable_multiline=False)
        assert isinstance(t, TextElement)
        assert t._get_text() == "hello"

    def test_text_with_reactive(self):
        r = Signal("world")
        t = text(r, enable_multiline=False)
        assert isinstance(t, TextElement)
        assert t._text is r

    def test_break_line_creates_newline(self):
        br = break_line()
        assert br._render_html() == "<br>"

    def test_switch_creates_switch_element(self):
        r = Signal(True)
        gen = switch({"case": r, "generator": lambda: text("yes")}, default=lambda: text("no"))
        cases = gen._cases
        assert len(cases) == 1
        assert cases[0][0] is r
        assert gen._default is not None

    def test_repeat_creates_repeat_element(self):
        rl = ReactiveList([1, 2, 3])
        rep = repeat(rl, lambda x: text(str(x)))
        assert rep._sequence is rl


class TestElementRenderHtml:
    def test_render_simple_element(self):
        el = create_element("div", {"class": "container"})
        el._parent = _make_parent()
        html = el._render_html()
        assert "div" in html
        assert "container" in html

    def test_render_with_children(self):
        el = create_element("p", {}, text("hello"))
        el._parent = _make_parent()
        html = el._render_html()
        assert "hello" in html

    def test_render_boolean_attr(self):
        el = create_element("input", {"disabled": True})
        el._parent = _make_parent()
        html = el._render_html()
        assert "disabled" in html

    def test_render_false_attr_omitted(self):
        el = create_element("input", {"disabled": False})
        el._parent = _make_parent()
        html = el._render_html()
        assert "disabled" not in html
