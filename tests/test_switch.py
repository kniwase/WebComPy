from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import TextElement
from webcompy.signal import Signal


class TestSelectGenerator:
    def test_selects_truthy_case(self):
        cases = [(True, lambda: "yes"), (False, lambda: "no")]
        sw = SwitchElement(cases, None)
        idx, gen = sw._select_generator()
        assert idx == 0
        assert gen() == "yes"

    def test_selects_second_truthy_case(self):
        cases = [(False, lambda: "no"), (True, lambda: "yes")]
        sw = SwitchElement(cases, None)
        idx, gen = sw._select_generator()
        assert idx == 1
        assert gen() == "yes"

    def test_falls_back_to_default(self):
        cases = [(False, lambda: "no")]
        sw = SwitchElement(cases, lambda: "default")
        idx, gen = sw._select_generator()
        assert idx == -1
        assert gen() == "default"

    def test_no_default_returns_none(self):
        cases = [(False, lambda: "no")]
        sw = SwitchElement(cases, None)
        idx, gen = sw._select_generator()
        assert idx == -1
        assert gen() is None

    def test_reactive_condition_truthy(self):
        cond = Signal(True)
        cases = [(cond, lambda: "reactive-yes")]
        sw = SwitchElement(cases, None)
        idx, gen = sw._select_generator()
        assert idx == 0
        assert gen() == "reactive-yes"

    def test_reactive_condition_falsy(self):
        cond = Signal(False)
        cases = [(cond, lambda: "reactive-no")]
        sw = SwitchElement(cases, lambda: "fallback")
        idx, gen = sw._select_generator()
        assert idx == -1
        assert gen() == "fallback"

    def test_reactive_cases_list(self):
        r = Signal([("hello", lambda: "ok")])
        sw = SwitchElement(r, None)
        idx, _gen = sw._select_generator()
        assert idx == 0


class TestOnSetParent:
    def test_on_set_parent_initializes_children(self):
        from tests.conftest import FakeDOMNode
        from webcompy.elements.types._element import Element

        class FakeRootElement(Element):
            _get_belonging_component = lambda self: ""
            _get_belonging_components = lambda self: ()

        cases = [(True, lambda: TextElement("yes"))]
        sw = SwitchElement(cases, None)
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        sw._parent = parent
        sw._node_idx = 0
        sw._on_set_parent()
        assert len(sw._children) == 1
        assert sw._rendered_idx == 0

    def test_on_set_parent_registers_reactive_callback(self):
        from tests.conftest import FakeDOMNode
        from webcompy.elements.types._element import Element

        class FakeRootElement(Element):
            _get_belonging_component = lambda self: ""
            _get_belonging_components = lambda self: ()

        cond = Signal(True)
        cases = [(cond, lambda: TextElement("yes"))]
        sw = SwitchElement(cases, None)
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        sw._parent = parent
        sw._node_idx = 0
        sw._on_set_parent()
        assert sw._signal_activated is True
        assert len(sw._callback_nodes) > 0
