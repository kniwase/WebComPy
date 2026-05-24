from __future__ import annotations

import sys

import pytest

E2E_DIR = __import__("pathlib").Path(__file__).parent.parent / "tests" / "e2e"


@pytest.fixture(autouse=True)
def _add_e2e_path(monkeypatch):
    monkeypatch.setattr(sys, "path", [str(E2E_DIR), *sys.path])


class TestScopedCssSSGOutput:
    def test_per_component_style_elements_in_html(self):
        from my_app.pages.scoped_style import ScopedStylePage

        from webcompy.app import WebComPyApp, WebComPyAppConfig
        from webcompy.cli._html import generate_html
        from webcompy.router import Router

        router = Router({"path": "/scoped", "component": ScopedStylePage}, mode="history")
        app = WebComPyApp(root_component=ScopedStylePage, router=router, config=WebComPyAppConfig(base_url="/"))
        with app.di_scope:
            html_str = generate_html(
                app,
                app_package_name="test",
                dev_mode=False,
                prerender=True,
                app_version="0+sha.test",
                wheel_filename="test-0+sha.test-py3-none-any.whl",
            )
        assert 'data-webcompy-cid="' in html_str

    def test_hidden_rule_present_in_html(self):
        from my_app.pages.scoped_style import ScopedStylePage

        from webcompy.app import WebComPyApp, WebComPyAppConfig
        from webcompy.cli._html import generate_html
        from webcompy.router import Router

        router = Router({"path": "/scoped", "component": ScopedStylePage}, mode="history")
        app = WebComPyApp(root_component=ScopedStylePage, router=router, config=WebComPyAppConfig(base_url="/"))
        with app.di_scope:
            html_str = generate_html(
                app,
                app_package_name="test",
                dev_mode=False,
                prerender=True,
                app_version="0+sha.test",
                wheel_filename="test-0+sha.test-py3-none-any.whl",
            )
        assert "*[hidden]{display: none;}" in html_str

    def test_scoped_css_not_present_for_no_style_component(self):
        from my_app.pages.home import HomePage

        from webcompy.app import WebComPyApp, WebComPyAppConfig
        from webcompy.cli._html import generate_html
        from webcompy.router import Router

        router = Router({"path": "/", "component": HomePage}, mode="history")
        app = WebComPyApp(root_component=HomePage, router=router, config=WebComPyAppConfig(base_url="/"))
        with app.di_scope:
            html_str = generate_html(
                app,
                app_package_name="test",
                dev_mode=False,
                prerender=True,
                app_version="0+sha.test",
                wheel_filename="test-0+sha.test-py3-none-any.whl",
            )
        assert 'data-webcompy-cid="' not in html_str


class TestHeadElementBrowserPath:
    def test_hidden_rule_injected_into_head(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            head_element._render()

            head_el = port.query_selector("head")
            assert head_el is not None

            style_el = _find_child_by_id(head_el, "webcompy-scoped-styles")
            assert style_el is not None
            assert "*[hidden]{display: none;}" in (style_el.textContent or "")
        finally:
            _active_di_scope.reset(token)

    def test_per_component_styles_injected(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen1 = ComponentGenerator("CompA", _noop)
        gen1.scoped_style = {".foo": {"color": "red"}}

        gen2 = ComponentGenerator("CompB", _noop)
        gen2.scoped_style = {".bar": {"color": "blue"}}

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        store.add_component("CompA", gen1)
        store.add_component("CompB", gen2)
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            head_element._render()

            head_el = port.query_selector("head")
            assert head_el is not None

            style_a = _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid", gen1._id)
            assert style_a is not None
            assert "color: red" in (style_a.textContent or "")

            style_b = _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid", gen2._id)
            assert style_b is not None
            assert "color: blue" in (style_b.textContent or "")
        finally:
            _active_di_scope.reset(token)

    def test_no_style_for_empty_scoped_style(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen = ComponentGenerator("NoStyleComp", _noop)

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        store.add_component("NoStyleComp", gen)
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            head_element._render()

            head_el = port.query_selector("head")
            assert head_el is not None
            assert _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid", gen._id) is None
        finally:
            _active_di_scope.reset(token)

    def test_reconcile_idempotent_no_duplicates(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen = ComponentGenerator("TestComp", _noop)
        gen.scoped_style = {".test": {"color": "red"}}

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        store.add_component("TestComp", gen)
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            head_element._render()

            head_el = port.query_selector("head")
            styles = _find_all_children_by_tag(head_el, "style")
            initial_count = len(styles)

            head_element._render()

            head_el = port.query_selector("head")
            styles = _find_all_children_by_tag(head_el, "style")
            assert len(styles) == initial_count
        finally:
            _active_di_scope.reset(token)

    def test_noop_when_not_pyscript(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "server")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen = ComponentGenerator("TestComp", _noop)
        gen.scoped_style = {".test": {"color": "red"}}

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        store.add_component("TestComp", gen)
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            head_element._render()

            head_el = port.query_selector("head")
            assert _find_child_by_id(head_el, "webcompy-scoped-styles") is None
        finally:
            _active_di_scope.reset(token)


class TestFakeBrowserDOMPortExtended:
    def test_query_selector_head(self):
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        result = port.query_selector("head")
        assert result is not None
        assert result.nodeName == "HEAD"

    def test_query_selector_body(self):
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        result = port.query_selector("body")
        assert result is not None
        assert result.nodeName == "BODY"

    def test_query_selector_nonexistent(self):
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        result = port.query_selector("footer")
        assert result is None

    def test_get_element_by_id(self):
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head = port.query_selector("head")
        style = port.create_element("style")
        style.setAttribute("id", "test-id")
        head.appendChild(style)

        result = port.get_element_by_id("test-id")
        assert result is not None
        assert result.getAttribute("id") == "test-id"

    def test_get_element_by_id_not_found(self):
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        result = port.get_element_by_id("nonexistent")
        assert result is None

    def test_query_selector_attribute(self):
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head = port.query_selector("head")
        style = port.create_element("style")
        style.setAttribute("data-webcompy-cid", "abc123")
        head.appendChild(style)

        result = port.query_selector('style[data-webcompy-cid="abc123"]')
        assert result is not None
        assert result.getAttribute("data-webcompy-cid") == "abc123"

    def test_append_child_persists(self):
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head = port.query_selector("head")
        el = port.create_element("div")
        head.appendChild(el)

        head2 = port.query_selector("head")
        divs = _find_all_children_by_tag(head2, "div")
        assert len(divs) == 1

    def test_inherits_render_html(self):
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        div = port.create_element("div")
        div.setAttribute("class", "test")
        div.textContent = "hello"
        html = port.render_html(div)
        assert '<div class="test">hello</div>' in html

    def test_create_element_returns_fake_dom_node(self):
        from webcompy.testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        el = port.create_element("span")
        assert el.nodeName == "SPAN"
        assert el.__webcompy_prerendered_node__ is False


def _find_child_by_id(node, element_id):
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if child.nodeName != "#text" and child.getAttribute("id") == element_id:
            return child
    return None


def _find_child_by_tag_attr(node, tag, attr_name, attr_value):
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if child.nodeName == tag.upper() and child.getAttribute(attr_name) == attr_value:
            return child
    return None


def _find_all_children_by_tag(node, tag):
    results = []
    tag_upper = tag.upper()
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if child.nodeName == tag_upper:
            results.append(child)
    return results
