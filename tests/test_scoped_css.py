from __future__ import annotations

import sys

import pytest

E2E_DIR = __import__("pathlib").Path(__file__).parent.parent.parent / "e2e" / "core"


@pytest.fixture(autouse=True)
def _add_e2e_path(monkeypatch):
    monkeypatch.setattr(sys, "path", [str(E2E_DIR), *sys.path])


class TestScopedCssSSGOutput:
    def test_per_component_style_elements_in_html(self):
        from my_app.pages.scoped_style import ScopedStylePage

        from webcompy.app import WebComPyApp, WebComPyAppConfig
        from webcompy.router import Router
        from webcompy_testing import render_app_html

        router = Router({"path": "/scoped", "component": ScopedStylePage}, mode="history")
        app = WebComPyApp(root_component=ScopedStylePage, router=router, config=WebComPyAppConfig(base_url="/"))
        html_str = render_app_html(
            app,
            path="/scoped",
            app_package_name="test",
            dev_mode=False,
            prerender=True,
            wheel_filename="test-0+sha.test-py3-none-any.whl",
        )
        assert 'data-webcompy-cid="' in html_str

    def test_hidden_rule_present_in_html(self):
        from my_app.pages.scoped_style import ScopedStylePage

        from webcompy.app import WebComPyApp, WebComPyAppConfig
        from webcompy.router import Router
        from webcompy_testing import render_app_html

        router = Router({"path": "/scoped", "component": ScopedStylePage}, mode="history")
        app = WebComPyApp(root_component=ScopedStylePage, router=router, config=WebComPyAppConfig(base_url="/"))
        html_str = render_app_html(
            app,
            path="/scoped",
            app_package_name="test",
            dev_mode=False,
            prerender=True,
            wheel_filename="test-0+sha.test-py3-none-any.whl",
        )
        assert "*[hidden]{display: none;}" in html_str

    def test_component_default_display_rule_present_in_html(self):
        from my_app.pages.home import HomePage

        from webcompy.app import WebComPyApp, WebComPyAppConfig
        from webcompy.router import Router
        from webcompy_testing import render_app_html

        router = Router({"path": "/", "component": HomePage}, mode="history")
        app = WebComPyApp(root_component=HomePage, router=router, config=WebComPyAppConfig(base_url="/"))
        html_str = render_app_html(
            app,
            path="/",
            app_package_name="test",
            dev_mode=False,
            prerender=True,
            wheel_filename="test-0+sha.test-py3-none-any.whl",
        )
        assert 'id="webcompy-component-defaults"' in html_str
        assert "[webcompy-component] { display: contents; }" in html_str

    def test_component_default_display_rule_follows_index_css_link(self):
        from my_app.pages.home import HomePage

        from webcompy.app import WebComPyApp, WebComPyAppConfig
        from webcompy.router import Router
        from webcompy_testing import render_app_html

        router = Router({"path": "/", "component": HomePage}, mode="history")
        app = WebComPyApp(root_component=HomePage, router=router, config=WebComPyAppConfig(base_url="/"))
        html_str = render_app_html(
            app,
            path="/",
            app_package_name="test",
            dev_mode=False,
            prerender=True,
            wheel_filename="test-0+sha.test-py3-none-any.whl",
        )
        link_pos = html_str.find("/_webcompy-ui/index.css")
        default_pos = html_str.find('id="webcompy-component-defaults"')
        assert link_pos != -1
        assert default_pos != -1
        assert link_pos < default_pos, "Default wrapper rule must follow the index.css layer-order declaration"

    def test_scoped_css_not_present_for_no_style_component(self):
        from my_app.pages.home import HomePage

        from webcompy.app import WebComPyApp, WebComPyAppConfig
        from webcompy.router import Router
        from webcompy_testing import render_app_html

        router = Router({"path": "/", "component": HomePage}, mode="history")
        app = WebComPyApp(root_component=HomePage, router=router, config=WebComPyAppConfig(base_url="/"))
        html_str = render_app_html(
            app,
            path="/",
            app_package_name="test",
            dev_mode=False,
            prerender=True,
            wheel_filename="test-0+sha.test-py3-none-any.whl",
        )
        assert 'data-webcompy-cid="' not in html_str


class TestHeadElementBrowserPath:
    @pytest.mark.asyncio
    async def test_hidden_rule_injected_into_head(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            await head_element._render()

            head_el = port.query_selector("head")
            assert head_el is not None

            style_el = _find_child_by_id(head_el, "webcompy-scoped-styles")
            assert style_el is not None
            assert "*[hidden]{display: none;}" in (style_el.textContent or "")

            default_el = _find_child_by_id(head_el, "webcompy-component-defaults")
            assert default_el is not None
            assert "[webcompy-component] { display: contents; }" in (default_el.textContent or "")

            await head_element._render()

            head_el = port.query_selector("head")
            defaults = _find_all_children_by_id(head_el, "webcompy-component-defaults")
            assert len(defaults) == 1, "Default wrapper rule must be injected exactly once"
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_per_component_styles_injected(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen1 = ComponentGenerator("CompA", _noop, custom_element_name="comp-a")
        gen1.scoped_style = {".foo": {"color": "red"}}

        gen2 = ComponentGenerator("CompB", _noop, custom_element_name="comp-b")
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
            await head_element._render()

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

    @pytest.mark.asyncio
    async def test_no_style_for_empty_scoped_style(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen = ComponentGenerator("NoStyleComp", _noop, custom_element_name="no-style-comp")

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
            await head_element._render()

            head_el = port.query_selector("head")
            assert head_el is not None
            assert _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid", gen._id) is None
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_reconcile_idempotent_no_duplicates(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen = ComponentGenerator("TestComp", _noop, custom_element_name="test-comp")
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
            await head_element._render()

            head_el = port.query_selector("head")
            styles = _find_all_children_by_tag(head_el, "style")
            initial_count = len(styles)

            await head_element._render()

            head_el = port.query_selector("head")
            styles = _find_all_children_by_tag(head_el, "style")
            assert len(styles) == initial_count
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_default_rule_precedes_component_styles(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen = ComponentGenerator("CompA", _noop, custom_element_name="comp-a")
        gen.scoped_style = {".foo": {"color": "red"}}

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        store.add_component("CompA", gen)
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_el = port.query_selector("head")
            assert head_el is not None

            # Simulate registration-time injection: a cid and a cid-rx style
            # element already exist in <head> before the first render.
            cid_el = port.create_element("style")
            cid_el.setAttribute("data-webcompy-cid", gen._id)
            cid_el.textContent = "@layer webcompy-scope { .foo[webcompy-cid-x] { color: red; } }"
            head_el.appendChild(cid_el)

            rx_el = port.create_element("style")
            rx_el.setAttribute("data-webcompy-cid-rx", f"{gen._id}-0")
            rx_el.textContent = "@layer webcompy-scope { .bar { color: blue; } }"
            head_el.appendChild(rx_el)

            head_element = HeadElement(head_props)
            await head_element._render()

            head_el = port.query_selector("head")
            default_idx = _index_of_child_with_id(head_el, "webcompy-component-defaults")
            cid_idx = _index_of_child_with_attr(head_el, "data-webcompy-cid", gen._id)
            rx_idx = _index_of_child_with_attr(head_el, "data-webcompy-cid-rx", f"{gen._id}-0")
            assert default_idx != -1
            assert cid_idx != -1
            assert rx_idx != -1
            assert default_idx < cid_idx, (
                "wrapper display default must precede component style elements so its "
                "@layer components is declared before @layer webcompy-scope"
            )
            assert default_idx < rx_idx

            default_el = _find_child_by_id(head_el, "webcompy-component-defaults")
            assert "[webcompy-component] { display: contents; }" in (default_el.textContent or "")
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_default_rule_precedes_component_styles_when_only_cid_present(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen = ComponentGenerator("CompA", _noop, custom_element_name="comp-a")
        gen.scoped_style = {".foo": {"color": "red"}}

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        store.add_component("CompA", gen)
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_el = port.query_selector("head")
            assert head_el is not None

            cid_el = port.create_element("style")
            cid_el.setAttribute("data-webcompy-cid", gen._id)
            cid_el.textContent = "@layer webcompy-scope { .foo[webcompy-cid-x] { color: red; } }"
            head_el.appendChild(cid_el)

            head_element = HeadElement(head_props)
            await head_element._render()

            head_el = port.query_selector("head")
            default_idx = _index_of_child_with_id(head_el, "webcompy-component-defaults")
            cid_idx = _index_of_child_with_attr(head_el, "data-webcompy-cid", gen._id)
            assert default_idx != -1
            assert cid_idx != -1
            assert default_idx < cid_idx
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_default_rule_appends_when_no_component_styles(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            await head_element._render()

            head_el = port.query_selector("head")
            default_idx = _index_of_child_with_id(head_el, "webcompy-component-defaults")
            assert default_idx != -1
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_default_rule_position_stable_across_renders(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen = ComponentGenerator("CompA", _noop, custom_element_name="comp-a")
        gen.scoped_style = {".foo": {"color": "red"}}

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        store.add_component("CompA", gen)
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_el = port.query_selector("head")
            assert head_el is not None

            cid_el = port.create_element("style")
            cid_el.setAttribute("data-webcompy-cid", gen._id)
            cid_el.textContent = "@layer webcompy-scope { .foo[webcompy-cid-x] { color: red; } }"
            head_el.appendChild(cid_el)

            head_element = HeadElement(head_props)
            await head_element._render()
            await head_element._render()

            head_el = port.query_selector("head")
            default_idx = _index_of_child_with_id(head_el, "webcompy-component-defaults")
            cid_idx = _index_of_child_with_attr(head_el, "data-webcompy-cid", gen._id)
            assert default_idx < cid_idx
            assert (
                _find_all_children_by_id(head_el, "webcompy-component-defaults")
                and len(_find_all_children_by_id(head_el, "webcompy-component-defaults")) == 1
            )
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_noop_when_not_pyscript(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "server")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentGenerator, ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        def _noop(ctx):
            pass

        gen = ComponentGenerator("TestComp", _noop, custom_element_name="test-comp")
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
            await head_element._render()

            head_el = port.query_selector("head")
            assert _find_child_by_id(head_el, "webcompy-scoped-styles") is None
        finally:
            _active_di_scope.reset(token)


class TestFakeBrowserDOMPortExtended:
    def test_query_selector_head(self):
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        result = port.query_selector("head")
        assert result is not None
        assert result.nodeName == "HEAD"

    def test_query_selector_body(self):
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        result = port.query_selector("body")
        assert result is not None
        assert result.nodeName == "BODY"

    def test_query_selector_nonexistent(self):
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        result = port.query_selector("footer")
        assert result is None

    def test_get_element_by_id(self):
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head = port.query_selector("head")
        style = port.create_element("style")
        style.setAttribute("id", "test-id")
        head.appendChild(style)

        result = port.get_element_by_id("test-id")
        assert result is not None
        assert result.getAttribute("id") == "test-id"

    def test_get_element_by_id_not_found(self):
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        result = port.get_element_by_id("nonexistent")
        assert result is None

    def test_query_selector_attribute(self):
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head = port.query_selector("head")
        style = port.create_element("style")
        style.setAttribute("data-webcompy-cid", "abc123")
        head.appendChild(style)

        result = port.query_selector('style[data-webcompy-cid="abc123"]')
        assert result is not None
        assert result.getAttribute("data-webcompy-cid") == "abc123"

    def test_append_child_persists(self):
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head = port.query_selector("head")
        el = port.create_element("div")
        head.appendChild(el)

        head2 = port.query_selector("head")
        divs = _find_all_children_by_tag(head2, "div")
        assert len(divs) == 1

    def test_inherits_render_html(self):
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        div = port.create_element("div")
        div.setAttribute("class", "test")
        div.textContent = "hello"
        html = port.render_html(div)
        assert '<div class="test">hello</div>' in html

    def test_create_element_returns_fake_dom_node(self):
        from webcompy_testing._ports import FakeBrowserDOMPort

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


def _index_of_child_with_id(node, element_id):
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if child.nodeName != "#text" and child.getAttribute("id") == element_id:
            return i
    return -1


def _index_of_child_with_attr(node, attr_name, attr_value):
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if child.nodeName != "#text" and child.getAttribute(attr_name) == attr_value:
            return i
    return -1


def _find_all_children_by_id(node, element_id):
    results = []
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if child.nodeName != "#text" and child.getAttribute("id") == element_id:
            results.append(child)
    return results


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
