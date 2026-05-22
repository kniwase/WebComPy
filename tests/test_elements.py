from typing import Protocol
from unittest.mock import MagicMock

from webcompy.di._scope import DIScope, _active_di_scope
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
from webcompy.ports._keys import DOM_PORT_KEY
from webcompy.ports._server._dom import ServerDOMPort
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
        from webcompy.elements.types._text import NewLine

        br = break_line()
        assert isinstance(br, NewLine)

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
    def _render_element_html(self, el):
        port = ServerDOMPort()
        root_node = port.create_element("div")
        root_node.__webcompy_node__ = False
        root_node.__webcompy_prerendered_node__ = True

        class _DummyParent:
            def __init__(self, node):
                self._node = node

            def _get_node(self):
                return self._node

            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

            def _re_index_children(self, recursive):
                pass

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        token = _active_di_scope.set(scope)
        try:
            el._parent = _DummyParent(root_node)
            el._node_idx = 0
            el._render()
            root_child = root_node.childNodes[0] if root_node.childNodes.length > 0 else None
            if root_child is None:
                return ""
            return port.render_html(root_child)
        finally:
            _active_di_scope.reset(token)

    def test_render_simple_element(self):
        el = create_element("div", {"class": "container"})
        html = self._render_element_html(el)
        assert "div" in html
        assert "container" in html

    def test_render_with_children(self):
        el = create_element("p", {}, TextElement("hello"))
        html = self._render_element_html(el)
        assert "hello" in html

    def test_render_boolean_attr(self):
        el = create_element("input", {"disabled": True})
        html = self._render_element_html(el)
        assert "disabled" in html

    def test_render_false_attr_omitted(self):
        el = create_element("input", {"disabled": False})
        html = self._render_element_html(el)
        assert "disabled" not in html
