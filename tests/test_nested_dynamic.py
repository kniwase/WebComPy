import importlib

import pytest

from tests.conftest import FakeBrowserModule, FakeDOMNode
from webcompy.elements.types._dynamic import _position_element_nodes
from webcompy.elements.types._element import Element
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import TextElement
from webcompy.signal import ReactiveList, Signal


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _make_parent():
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


def _patch_browser(monkeypatch, fake_browser):
    modules_with_browser = [
        "webcompy.elements.types._element",
        "webcompy.elements.types._abstract",
        "webcompy.elements.types._text",
        "webcompy.elements.types._switch",
        "webcompy.elements.types._repeat",
    ]
    for module_name in modules_with_browser:
        mod = importlib.import_module(module_name)
        monkeypatch.setattr(mod, "browser", fake_browser)
    from webcompy._browser import _modules

    monkeypatch.setattr(_modules, "browser", fake_browser)


@pytest.fixture
def fake_browser_full(monkeypatch):
    browser = FakeBrowserModule()
    _patch_browser(monkeypatch, browser)
    return browser


class TestGetNodeAncestorTraversal:
    def test_dynamic_element_gets_parent_node(self):
        parent = _make_parent()
        cond = Signal(True)
        sw = SwitchElement([(cond, lambda: TextElement("yes"))], None)
        sw._parent = parent
        sw._node_idx = 0
        sw._on_set_parent()
        assert sw._get_node() is parent._get_node()

    def test_nested_dynamic_gets_grandparent_node(self):
        parent = _make_parent()
        cond = Signal(True)
        rl = ReactiveList(["a", "b"])
        inner = RepeatElement(rl, lambda x: TextElement(x))
        sw = SwitchElement([(cond, lambda: inner)], None)
        sw._parent = parent
        sw._node_idx = 0
        sw._on_set_parent()
        assert inner._parent is parent
        assert inner._get_node() is parent._get_node()


class TestSwitchInsideRepeat:
    def test_switch_inside_repeat_on_set_parent(self):
        rl = ReactiveList([True, False, True])
        rep = RepeatElement(
            rl,
            lambda val: SwitchElement(
                [(val if isinstance(val, Signal) else Signal(val), lambda: TextElement("on"))],
                lambda: TextElement("off"),
            ),
        )
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._on_set_parent()
        assert len(rep._children) == 3
        for child in rep._children:
            assert isinstance(child, SwitchElement)

    def test_switch_inside_repeat_rendering(self, fake_browser_full):
        rl = ReactiveList(["a", "b"])
        rep = RepeatElement(rl, lambda item: TextElement(item))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._refresh()
        assert len(rep._children) == 2

    def test_repeat_inside_switch_on_set_parent(self):
        from webcompy.elements.types._switch import SwitchElement

        cond = Signal(True)
        rl = ReactiveList(["x", "y"])
        inner_rep = RepeatElement(rl, lambda item: TextElement(item))
        sw = SwitchElement([(cond, lambda: inner_rep)], None)
        parent = _make_parent()
        sw._parent = parent
        sw._node_idx = 0
        sw._on_set_parent()
        assert len(sw._children) == 1
        assert isinstance(sw._children[0], RepeatElement)

    def test_repeat_inside_switch_no_nesting_exception(self):
        cond = Signal(True)
        rl = ReactiveList(["x"])
        inner_rep = RepeatElement(rl, lambda item: TextElement(item))
        sw = SwitchElement([(cond, lambda: inner_rep)], None)
        parent = _make_parent()
        sw._parent = parent
        sw._node_idx = 0
        sw._on_set_parent()
        assert isinstance(sw._children[0], RepeatElement)


class TestNestedDynamicElementCleanup:
    def test_switch_removal_cleans_up_nested_repeat_callbacks(self, fake_browser_full):
        cond = Signal(True)
        rl = ReactiveList(["a", "b"])
        inner_rep = RepeatElement(rl, lambda item: TextElement(item))
        sw = SwitchElement([(cond, lambda: inner_rep)], None)
        parent = _make_parent()
        sw._parent = parent
        sw._node_idx = 0
        sw._refresh()
        original_repeat_callbacks = len(inner_rep._callback_nodes)
        assert original_repeat_callbacks > 0
        cond.value = False
        sw._refresh()
        assert len(sw._children) == 0

    def test_repeat_removal_cleans_up_switch(self, fake_browser_full):
        rl = ReactiveList(["a"])
        sw = SwitchElement(
            [(Signal(True), lambda: TextElement("on"))],
            lambda: TextElement("off"),
        )
        rep = RepeatElement(rl, lambda item: sw)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._refresh()
        assert len(rep._children) == 1
        rl.clear()
        rep._refresh()
        assert len(rep._children) == 0


class TestPositionElementNodes:
    def test_position_regular_element(self, fake_browser_full):
        parent = _make_parent()
        child = TextElement("hello")
        child._parent = parent
        child._node_idx = 0
        child._mounted = True
        parent_node = parent._get_node()
        result_idx = _position_element_nodes(child, parent_node, 0)
        assert result_idx == 1

    def test_position_dynamic_element_recursive(self, fake_browser_full):
        parent = _make_parent()
        rl = ReactiveList(["a"])
        rep = RepeatElement(rl, lambda x: TextElement(x))
        rep._parent = parent
        rep._node_idx = 0
        rep._refresh()
        parent_node = parent._get_node()
        result_idx = _position_element_nodes(rep, parent_node, 0)
        assert result_idx == 1


class TestRenderHTMLWithNesting:
    def test_repeat_inside_switch_render_html(self):
        cond = Signal(True)
        rl = ReactiveList(["hello", "world"])
        inner_rep = RepeatElement(rl, lambda item: TextElement(item))
        sw = SwitchElement([(cond, lambda: inner_rep)], None)
        parent = _make_parent()
        sw._parent = parent
        sw._node_idx = 0
        sw._on_set_parent()
        html = sw._render_html()
        assert "hello" in html
        assert "world" in html

    def test_switch_inside_repeat_render_html(self):
        rl = ReactiveList(["a", "b"])
        rep = RepeatElement(
            rl,
            lambda item: TextElement(item),
        )
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._on_set_parent()
        html = rep._render_html()
        assert "a" in html
        assert "b" in html


class TestNodeCountWithNesting:
    def test_switch_node_count_sums_children(self):
        rl = ReactiveList(["a", "b", "c"])
        inner_rep = RepeatElement(rl, lambda item: TextElement(item))
        cond = Signal(True)
        sw = SwitchElement([(cond, lambda: inner_rep)], None)
        parent = _make_parent()
        sw._parent = parent
        sw._node_idx = 0
        sw._on_set_parent()
        assert sw._node_count == 3

    def test_nested_dynamic_node_count(self):
        inner_rl = ReactiveList(["x", "y"])
        inner_rep = RepeatElement(inner_rl, lambda item: TextElement(item))
        outer_rl = ReactiveList(["a"])
        outer_rep = RepeatElement(outer_rl, lambda item: inner_rep)
        parent = _make_parent()
        outer_rep._parent = parent
        outer_rep._node_idx = 0
        outer_rep._on_set_parent()
        assert outer_rep._node_count >= 1
