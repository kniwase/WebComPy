from __future__ import annotations

import pytest

from tests.conftest import FakeDOMNode
from webcompy.app._config import AppConfig
from webcompy.elements.types._element import Element
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements.types._text import TextElement


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


class TestElementAdoptNode:
    def test_adopt_prerendered_node_sets_cache_and_mounted(self, fake_browser_full):
        el = _setup_element("div", {"class": "test"})
        node = FakeDOMNode("div")
        node.__webcompy_prerendered_node__ = True
        el._adopt_node(node)
        assert el._node_cache is node
        assert el._mounted is True

    def test_adopt_node_sets_webcompy_flag(self, fake_browser_full):
        el = _setup_element("div", {})
        node = FakeDOMNode("div")
        el._adopt_node(node)
        assert node.__webcompy_node__ is True

    def test_adopt_node_syncs_attributes(self, fake_browser_full):
        el = _setup_element("span", {"class": "new"})
        node = FakeDOMNode("span")
        node.setAttribute("class", "old")
        el._adopt_node(node)
        assert node.getAttribute("class") == "new"

    def test_adopt_node_removes_stale_attrs(self, fake_browser_full):
        el = _setup_element("span", {"class": "test"})
        node = FakeDOMNode("span")
        node.__webcompy_prerendered_node__ = True
        node.setAttribute("data-extra", "value")
        el._adopt_node(node)
        assert node.getAttribute("data-extra") is None

    def test_adopt_node_skips_setAttribute_when_matching(self, fake_browser_full):
        el = _setup_element("span", {"class": "test"})
        node = FakeDOMNode("span")
        node.setAttribute("class", "test")
        count_before = node.setAttribute_count
        el._adopt_node(node)
        assert node.setAttribute_count == count_before

    def test_adopt_node_registers_event_handler(self, fake_browser_full):
        handler = lambda ev: None
        el = _setup_element("div", {}, {"click": handler})
        node = FakeDOMNode("div")
        el._adopt_node(node)
        assert "click" in node._FakeDOMNode__event_listeners

    def test_adopt_node_initializes_ref(self, fake_browser_full):
        ref = DomNodeRef()
        el = _setup_element("div", {}, {}, ref)
        node = FakeDOMNode("div")
        el._adopt_node(node)
        assert ref._node is node

    def test_adopt_node_does_not_call_mount_node(self, fake_browser_full):
        el = _setup_element("div", {})
        node = FakeDOMNode("div")
        parent_node = el._parent._get_node()
        parent_node.appendChild(node)
        el._adopt_node(node)
        assert el._mounted is True
        assert parent_node.childNodes.length == 1

    def test_adopt_node_registers_signal_callback(self, fake_browser_full):
        from webcompy.signal import Signal

        value = Signal("initial")
        el = _setup_element("div", {"class": value})
        node = FakeDOMNode("div")
        el._adopt_node(node)
        assert node.getAttribute("class") == "initial"
        value.value = "updated"
        assert node.getAttribute("class") == "updated"


class TestTextElementAdoptNode:
    def test_adopt_prerendered_text_node(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        text_el = TextElement("hello")
        text_el._parent = parent
        text_el._node_idx = 0
        node = FakeDOMNode("#text", text_content="stale")
        text_el._adopt_node(node)
        assert text_el._node_cache is node
        assert text_el._mounted is True
        assert node.textContent == "hello"

    def test_adopt_text_node_skips_write_when_matching(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        node = FakeDOMNode("#text", text_content="hello")
        text_el = TextElement("hello")
        text_el._parent = parent
        text_el._node_idx = 0
        text_el._adopt_node(node)
        assert node.textContent_write_count == 0

    def test_adopt_text_node_writes_when_differing(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        node = FakeDOMNode("#text", text_content="stale")
        text_el = TextElement("hello")
        text_el._parent = parent
        text_el._node_idx = 0
        text_el._adopt_node(node)
        assert node.textContent_write_count == 1


class TestHydrateNode:
    def test_hydrate_node_adopts_prerendered_matching(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent_node = parent._get_node()
        existing_node = FakeDOMNode("span")
        existing_node.__webcompy_prerendered_node__ = True
        parent_node.appendChild(existing_node)
        el = Element("span", {"class": "test"}, {}, None, None)
        el._parent = parent
        el._node_idx = 0
        result = el._hydrate_node()
        assert result is existing_node
        assert el._mounted is True
        assert el._node_cache is existing_node

    def test_hydrate_node_falls_back_to_init_when_no_existing(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        el = Element("span", {"class": "test"}, {}, None, None)
        el._parent = parent
        el._node_idx = 0
        result = el._hydrate_node()
        assert result is not None
        assert result.__webcompy_node__ is True

    def test_hydrate_node_falls_back_when_tag_mismatch(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent_node = parent._get_node()
        existing_node = FakeDOMNode("p")
        existing_node.__webcompy_prerendered_node__ = True
        parent_node.appendChild(existing_node)
        el = Element("span", {}, {}, None, None)
        el._parent = parent
        el._node_idx = 0
        result = el._hydrate_node()
        assert result is not existing_node
        assert result.__webcompy_node__ is True

    def test_hydrate_node_text_element_adopts(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent_node = parent._get_node()
        existing_node = FakeDOMNode("#text", text_content="hello")
        existing_node.__webcompy_prerendered_node__ = True
        parent_node.appendChild(existing_node)
        text_el = TextElement("hello")
        text_el._parent = parent
        text_el._node_idx = 0
        result = text_el._hydrate_node()
        assert result is existing_node
        assert text_el._mounted is True


class TestAppConfigHydrate:
    def test_app_config_hydrate_default_true(self):
        config = AppConfig()
        assert config.hydrate is True

    def test_app_config_hydrate_false(self):
        config = AppConfig(hydrate=False)
        assert config.hydrate is False

    def test_app_config_hydrate_true(self):
        config = AppConfig(hydrate=True)
        assert config.hydrate is True


class TestWebComPyAppHydrate:
    def test_app_hydrate_default_true(self):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def HydrateRoot1(context):
            return html.DIV({}, "hello")

        app = WebComPyApp(root_component=HydrateRoot1)
        assert app._hydrate is True

    def test_app_hydrate_explicit_false(self):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def HydrateRoot2(context):
            return html.DIV({}, "hello")

        app = WebComPyApp(root_component=HydrateRoot2, hydrate=False)
        assert app._hydrate is False

    def test_app_hydrate_from_config(self):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def HydrateRoot3(context):
            return html.DIV({}, "hello")

        config = AppConfig(hydrate=False)
        app = WebComPyApp(root_component=HydrateRoot3, config=config)
        assert app._hydrate is False

    def test_app_hydrate_parameter_overrides_config(self):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def HydrateRoot4(context):
            return html.DIV({}, "hello")

        config = AppConfig(hydrate=True)
        app = WebComPyApp(root_component=HydrateRoot4, hydrate=False, config=config)
        assert app._hydrate is False
