from __future__ import annotations

import pytest
from webcompy.exception import WebComPyException
from webcompy.elements.types._text import TextElement, NewLine
from webcompy.elements.types._element import Element, _generate_event_handler
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements.types._abstract import ElementAbstract
from tests.conftest import FakeDOMNode


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _patch_browser(monkeypatch, fake_browser):
    import importlib

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


def _setup_element(tag="div", attrs=None, events=None, ref=None, children=None):
    root = FakeRootElement("div", {}, {}, None, None)
    root._node_cache = FakeDOMNode("div")
    root._mounted = True
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._parent = root
    parent._node_idx = 0
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    el = Element(tag, attrs or {}, events or {}, ref, children)
    el._parent = parent
    el._node_idx = 0
    return el


@pytest.fixture
def fake_browser_full(monkeypatch):
    from tests.conftest import FakeBrowserModule

    browser = FakeBrowserModule()
    _patch_browser(monkeypatch, browser)
    return browser


class TestElementInitNode:
    def test_init_node_creates_element(self, fake_browser_full):
        el = _setup_element("span", {"class": "test"})
        node = el._init_node()
        assert node is not None
        assert node.__webcompy_node__ is True

    def test_init_node_sets_attributes(self, fake_browser_full):
        el = _setup_element("div", {"class": "container", "id": "main"})
        node = el._init_node()
        assert node.getAttribute("class") == "container"
        assert node.getAttribute("id") == "main"

    def test_init_node_registers_event_handler(self, fake_browser_full):
        handler = lambda ev: None
        el = _setup_element("div", {}, {"click": handler})
        node = el._init_node()
        assert "click" in node._FakeDOMNode__event_listeners

    def test_init_node_sets_ref(self, fake_browser_full):
        ref = DomNodeRef()
        el = _setup_element("div", {}, {}, ref)
        node = el._init_node()
        assert ref._node is node

    def test_init_node_boolean_true_attr(self, fake_browser_full):
        el = _setup_element("input", {"disabled": True})
        node = el._init_node()
        assert node.getAttribute("disabled") == ""

    def test_init_node_boolean_false_attr(self, fake_browser_full):
        el = _setup_element("input", {"disabled": False})
        node = el._init_node()
        assert node.getAttribute("disabled") is None

    def test_generate_event_handler_returns_callable(self, fake_browser_full):
        handler = lambda ev: None
        result = _generate_event_handler(handler)
        assert callable(result)

    def test_generate_event_handler_proxy_has_destroy(self, fake_browser_full):
        handler = lambda ev: None
        result = _generate_event_handler(handler)
        assert hasattr(result, "destroy")
        result.destroy()


class TestElementUpdateAttr:
    def test_attr_updater_removes_attribute_on_bool_false(self, fake_browser_full):
        from webcompy.reactive import Reactive

        value = Reactive(True)
        el = _setup_element("input", {"disabled": value})
        el._init_node()
        node = el._get_node()
        assert "disabled" in node.getAttributeNames()
        value.value = False
        assert "disabled" not in node.getAttributeNames()

    def test_attr_updater_sets_attribute(self, fake_browser_full):
        el = _setup_element("div", {"class": "old"})
        el._init_node()
        updater = el._generate_attr_updater("class")
        updater("new")
        assert el._get_node().getAttribute("class") == "new"


class TestElementRemoveElement:
    def test_remove_element_resets_ref(self, fake_browser_full):
        ref = DomNodeRef()
        el = _setup_element("div", {}, {}, ref)
        el._init_node()
        el._remove_element(remove_node=False)
        assert ref._node is None


class TestElementNoBrowser:
    def test_init_node_raises_without_browser(self):
        el = Element("div", {}, {}, None, None)
        parent = Element("div", {}, {}, None, None)
        el._parent = parent
        el._node_idx = 0
        try:
            el._init_node()
            assert False, "Should have raised"
        except WebComPyException as e:
            assert "Not in Browser" in str(e)

    def test_text_init_node_raises_without_browser(self):
        text_el = TextElement("hello")
        parent = Element("div", {}, {}, None, None)
        text_el._parent = parent
        text_el._node_idx = 0
        try:
            text_el._init_node()
            assert False, "Should have raised"
        except WebComPyException:
            pass

    def test_newline_init_node_raises_without_browser(self):
        br = NewLine()
        parent = Element("div", {}, {}, None, None)
        br._parent = parent
        br._node_idx = 0
        try:
            br._init_node()
            assert False, "Should have raised"
        except WebComPyException:
            pass


class TestTextElementWithBrowser:
    def test_init_node_creates_text_node(self, fake_browser_full):
        parent = Element("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        text_el = TextElement("hello")
        text_el._parent = parent
        text_el._node_idx = 0
        node = text_el._init_node()
        assert node is not None
        assert node.textContent == "hello"

    def test_update_text_node_content(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        text_el = TextElement("hello")
        text_el._parent = parent
        text_el._node_idx = 0
        text_el._init_node()
        text_el._update_text("changed")
        assert text_el._get_node().textContent == "changed"

    def test_text_update_without_browser(self):
        text_el = TextElement("hello")
        text_el._update_text("world")
        assert text_el._text == "world"


class TestNewLineWithBrowser:
    def test_init_node_creates_br(self, fake_browser_full):
        parent = Element("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        br = NewLine()
        br._parent = parent
        br._node_idx = 0
        node = br._init_node()
        assert node is not None
        assert node.nodeName == "BR"


class TestElementAbstractWithBrowser:
    def test_mount_node_appends_to_parent(self, fake_browser_full):
        root = FakeRootElement("div", {}, {}, None, None)
        root._node_cache = FakeDOMNode("div")
        root._mounted = True
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._parent = root
        parent._node_idx = 0
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        el = FakeRootElement("span", {}, {}, None, None)
        el._parent = parent
        el._node_idx = 0
        el._mounted = None
        el._get_node()
        parent_node = parent._get_node()
        assert len(parent_node.childNodes._nodes) == 0
        el._mount_node()
        assert el._mounted is True
        assert len(parent_node.childNodes._nodes) == 1

    def test_detach_node_creates_placeholder(self, fake_browser_full):
        root = FakeRootElement("div", {}, {}, None, None)
        root._node_cache = FakeDOMNode("div")
        root._mounted = True
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._parent = root
        parent._node_idx = 0
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        el = FakeRootElement("span", {}, {}, None, None)
        el._parent = parent
        el._node_idx = 0
        el._mounted = None
        el._get_node()
        el._mount_node()
        assert el._mounted is True
        el._detach_node()
        assert el._mounted is False
        assert el._remount_to is not None


class TestReactiveAttrUpdate:
    def test_reactive_attr_registers_callback(self, fake_browser_full):
        from webcompy.reactive import Reactive

        value = Reactive("initial")
        el = _setup_element("div", {"class": value})
        el._init_node()
        node = el._get_node()
        assert node.getAttribute("class") == "initial"
        value.value = "updated"
        assert node.getAttribute("class") == "updated"
