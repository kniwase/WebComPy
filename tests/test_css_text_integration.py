from __future__ import annotations

import base64
from pathlib import Path

import pytest

from webcompy.components._generator import ComponentGenerator, define_component
from webcompy.components._reactive_scoped_style import reactive_scoped_style
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.ports._browser._resource import BrowserResourcePort
from webcompy.ports._fetch import Response
from webcompy.ports._keys import FETCH_PORT_KEY, RESOURCE_PORT_KEY
from webcompy.resources import load_text
from webcompy.signal import Signal
from webcompy.template import css_text, css_text_template
from webcompy_testing import TestRenderer


@pytest.fixture(autouse=True)
def _patch_environment(monkeypatch):
    monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")
    monkeypatch.setattr("webcompy.utils._environment.ENVIRONMENT", "pyscript")
    monkeypatch.setattr("webcompy.ports._browser._resource.ENVIRONMENT", "pyscript")


def _noop_setup(ctx):
    return html.DIV({}, "")


class TestStaticCssTextGenerator:
    def test_css_text_as_scoped_style_renders_scoped_css(self):
        gen = ComponentGenerator("CssTextStatic", _noop_setup, custom_element_name="css-text-static")
        gen.scoped_style = css_text(".btn { color: red; }")
        css = gen.scoped_style

        assert "@layer webcompy-scope" in css
        assert f".btn[webcompy-cid-{gen._id}]" in css
        assert "color: red" in css

    def test_css_text_output_equivalent_to_dict_form(self):
        gen_text = ComponentGenerator("CssTextGen", _noop_setup, custom_element_name="css-text-gen")
        gen_text.scoped_style = css_text(".btn { color: red; :hover { background: blue; } }")

        gen_dict = ComponentGenerator("DictGen", _noop_setup, custom_element_name="dict-gen")
        gen_dict.scoped_style = {".btn": {"color": "red", ":hover": {"background": "blue"}}}

        from re import sub

        normalised_text = sub(r"webcompy-cid-\w+", "CID", gen_text.scoped_style)
        normalised_dict = sub(r"webcompy-cid-\w+", "CID", gen_dict.scoped_style)

        assert normalised_text == normalised_dict

    def test_css_text_at_rule_renders_inside_layer(self):
        gen = ComponentGenerator("CssTextAtRule", _noop_setup, custom_element_name="css-text-at-rule")
        gen.scoped_style = css_text("@media (max-width: 768px) { .btn { font-size: 12px; } }")
        css = gen.scoped_style
        assert "@media (max-width: 768px)" in css
        assert f".btn[webcompy-cid-{gen._id}]" in css
        assert "font-size: 12px" in css

    def test_css_text_keyframes_renders(self):
        gen = ComponentGenerator("CssTextKf", _noop_setup, custom_element_name="css-text-kf")
        gen.scoped_style = css_text(
            "@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }"
        )
        css = gen.scoped_style
        assert "@keyframes spin" in css
        assert "rotate(0deg)" in css
        assert "rotate(360deg)" in css


class TestCssTextTemplateRegistration:
    def test_setup_execution_registers_css_text_template_with_reactive_scoped_style(
        self,
    ):
        color = Signal("blue")
        registered_ref: dict = {}

        @define_component("my-comp")
        def MyComp(context):
            style = reactive_scoped_style(css_text_template(".btn { color: {{ color }}; }", {"color": color}))
            context.use_reactive_scoped_style(style)
            registered_ref["style"] = style
            return html.DIV({}, "x")

        result = TestRenderer.render(MyComp)
        try:
            assert len(MyComp._reactive_styles) == 1
            registered = MyComp._reactive_styles[0]
            assert registered is registered_ref["style"]
            assert registered._cid == MyComp._id
            assert registered.dict_computed.value == {".btn": {"color": "blue"}}

            color.value = "red"
            assert registered.dict_computed.value == {".btn": {"color": "red"}}
        finally:
            result.close()


class TestReactiveStyleDomUpdate:
    @pytest.mark.asyncio
    async def test_signal_change_updates_style_element_text(self):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._hooks import _active_component_context
        from webcompy.components._libs import Context
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        color = Signal("blue")

        @define_component("rx-comp")
        def RxComp(context):
            return html.DIV({}, "")

        style = reactive_scoped_style(css_text_template(".btn { color: {{ color }}; }", {"color": color}))

        gen = RxComp

        store = _make_store("RxComp", RxComp)
        head_props = HeadPropsStore()

        ctx = Context(
            None,
            {},
            "RxComp",
            lambda: "",
            lambda: {},
            lambda _: None,
            lambda _, __: None,
            generator=gen,
        )

        port = FakeBrowserDOMPort()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        di_token = _active_di_scope.set(scope)
        ctx_token = _active_component_context.set(ctx)  # type: ignore[arg-type]
        try:
            ctx.use_reactive_scoped_style(style)

            head_element = HeadElement(head_props)
            await head_element._render()

            head_el = port.query_selector("head")
            assert head_el is not None
            rx_attr = f"{gen._id}-0"
            rx_el = _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid-rx", rx_attr)
            assert rx_el is not None
            initial = rx_el.textContent or ""
            assert "color: blue" in initial
            assert "color: red" not in initial

            color.value = "red"

            updated = rx_el.textContent or ""
            assert "color: red" in updated
        finally:
            _active_component_context.reset(ctx_token)
            _active_di_scope.reset(di_token)


class _RecordingFetchPort:
    def __init__(self, response: str = "from network") -> None:
        self.response = response
        self.calls: list[str] = []

    async def fetch(self, url: str, **_kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(url)
        return Response(
            text=self.response,
            content=self.response.encode("utf-8"),
            headers={"content-type": "text/plain"},
            status_code=200,
            status_text="OK",
            ok=True,
        )


class TestAsyncFileCssHydration:
    @pytest.mark.asyncio
    async def test_css_text_with_load_text_records_for_hydration(self, tmp_path: Path):
        from webcompy_server.ports._resource import ServerResourcePort

        pkg = tmp_path / "app"
        pkg.mkdir()
        (pkg / "card.css").write_text(".btn { color: red; }", encoding="utf-8")

        server_port = ServerResourcePort(pkg, frozenset({"card.css"}))

        scope = DIScope()
        scope.provide(RESOURCE_PORT_KEY, server_port)
        token = _active_di_scope.set(scope)
        try:
            text = await load_text("card.css")
            parsed = css_text(text)

            assert parsed == {".btn": {"color": "red"}}

            recorded = server_port.get_recorded_resources()
            assert "card.css" in recorded
            assert recorded["card.css"] == b".btn { color: red; }"
        finally:
            _active_di_scope.reset(token)
            scope.dispose()

    def test_async_component_setup_executes_css_text_with_load_text(self, tmp_path: Path):
        from webcompy_server.ports._resource import ServerResourcePort

        pkg = tmp_path / "app"
        pkg.mkdir()
        (pkg / "card.css").write_text(".btn { color: red; }", encoding="utf-8")

        server_port = ServerResourcePort(pkg, frozenset({"card.css"}))

        captured_server: dict = {}

        @define_component("server-comp")
        async def ServerComp(_):
            text = await load_text("card.css")
            parsed = css_text(text)
            captured_server["parsed"] = parsed
            return html.DIV({}, "server-card")

        parent_scope = DIScope()
        parent_scope.provide(RESOURCE_PORT_KEY, server_port)

        server_result = TestRenderer.render(ServerComp, parent_scope=parent_scope)
        try:
            assert server_result.find_by_text("server-card") is not None
            assert captured_server["parsed"] == {".btn": {"color": "red"}}

            recorded = server_port.get_recorded_resources()
            assert "card.css" in recorded
            assert recorded["card.css"] == b".btn { color: red; }"
        finally:
            server_result.close()

        from webcompy.di._keys import RESOURCE_DATA_KEY

        encoded = {path: base64.b64encode(content).decode("ascii") for path, content in recorded.items()}

        fetch_port = _RecordingFetchPort()
        browser_port = BrowserResourcePort(base_url="/")

        browser_parent_scope = DIScope()
        browser_parent_scope.provide(RESOURCE_DATA_KEY, encoded)
        browser_parent_scope.provide(FETCH_PORT_KEY, fetch_port)
        browser_parent_scope.provide(RESOURCE_PORT_KEY, browser_port)

        captured_browser: dict = {}

        @define_component("browser-comp")
        async def BrowserComp(_):
            text = await load_text("card.css")
            parsed = css_text(text)
            captured_browser["parsed"] = parsed
            return html.DIV({}, "browser-card")

        browser_result = TestRenderer.render(BrowserComp, parent_scope=browser_parent_scope)
        try:
            assert browser_result.find_by_text("browser-card") is not None
            assert captured_browser["parsed"] == {".btn": {"color": "red"}}
            assert fetch_port.calls == []
        finally:
            browser_result.close()


class TestDictScopedStyleRegression:
    def test_dict_scoped_style_still_produces_layered_css(self):
        gen = ComponentGenerator("DictStatic", _noop_setup, custom_element_name="dict-static")
        gen.scoped_style = {".btn": {"color": "red", ":hover": {"background": "blue"}}}
        css = gen.scoped_style

        assert "@layer webcompy-scope" in css
        assert f".btn[webcompy-cid-{gen._id}]" in css
        assert f".btn[webcompy-cid-{gen._id}]:hover" in css
        assert "color: red" in css
        assert "background: blue" in css

    def test_dict_keyframes_still_renders(self):
        gen = ComponentGenerator("DictKf", _noop_setup, custom_element_name="dict-kf")
        gen.scoped_style = {
            "@keyframes fade": {
                "from": {"opacity": "0"},
                "to": {"opacity": "1"},
            }
        }
        css = gen.scoped_style
        assert "@keyframes fade" in css
        assert "opacity: 0" in css or "opacity:0" in css.replace(" ", "")

    def test_dict_at_rule_still_emits_combinator_scoped_inner(self):
        gen = ComponentGenerator("DictMedia", _noop_setup, custom_element_name="dict-media")
        gen.scoped_style = {"@media (max-width: 768px)": {".btn": {"color": "red"}}}
        css = gen.scoped_style
        assert "@media (max-width: 768px)" in css
        assert f".btn[webcompy-cid-{gen._id}]" in css

    def test_dict_scoped_style_setter_rejects_string_assignment(self):
        gen = ComponentGenerator("DictRejected", _noop_setup, custom_element_name="dict-rejected")
        with pytest.raises(AttributeError):
            gen.scoped_style = ".btn { color: red; }"  # type: ignore[assignment]


class TestDictFactoryReactiveRegression:
    def test_dict_factory_reactive_scoped_style_tracks_signal(self):
        from webcompy.components._reactive_scoped_style import ReactiveScopedStyle

        color = Signal("blue")
        style = reactive_scoped_style(lambda: {".x": {"color": color.value}})
        assert isinstance(style, ReactiveScopedStyle)
        style._bind("test-dict-cid", host_tag="test-component")

        assert style.dict_computed.value == {".x": {"color": "blue"}}
        color.value = "red"
        assert style.dict_computed.value == {".x": {"color": "red"}}

    def test_dict_factory_render_css_matches_static(self):
        gen = ComponentGenerator("DictReactiveCompare", _noop_setup, custom_element_name="dict-reactive-compare")
        gen.scoped_style = {".btn": {"color": "blue"}}

        color = Signal("blue")
        style = reactive_scoped_style(lambda: {".btn": {"color": color.value}})
        style._bind(gen._id, host_tag="test-component")

        import re

        static_normalised = re.sub(r"webcompy-cid-\w+", "CID", gen.scoped_style)
        reactive_normalised = re.sub(r"webcompy-cid-\w+", "CID", style.render_css(gen._id))
        assert static_normalised == reactive_normalised

    @pytest.mark.asyncio
    async def test_dict_factory_signal_change_updates_dom_style_element(self):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._hooks import _active_component_context
        from webcompy.components._libs import Context
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        color = Signal("blue")

        @define_component("dict-rx-comp")
        def DictRxComp(context):
            return html.DIV({}, "")

        gen = DictRxComp

        style = reactive_scoped_style(lambda: {".dyn": {"color": color.value}})

        store = _make_store("DictRxComp", DictRxComp)
        head_props = HeadPropsStore()
        ctx = Context(
            None,
            {},
            "DictRxComp",
            lambda: "",
            lambda: {},
            lambda _: None,
            lambda _, __: None,
            generator=gen,
        )

        port = FakeBrowserDOMPort()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        di_token = _active_di_scope.set(scope)
        ctx_token = _active_component_context.set(ctx)  # type: ignore[arg-type]
        try:
            ctx.use_reactive_scoped_style(style)

            head_element = HeadElement(head_props)
            await head_element._render()

            head_el = port.query_selector("head")
            rx_attr = f"{gen._id}-0"
            rx_el = _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid-rx", rx_attr)
            assert rx_el is not None
            assert "color: blue" in (rx_el.textContent or "")

            color.value = "red"

            assert "color: red" in (rx_el.textContent or "")
        finally:
            _active_component_context.reset(ctx_token)
            _active_di_scope.reset(di_token)


def _make_store(name: str, gen: ComponentGenerator):
    from webcompy.components._generator import ComponentStore

    store = ComponentStore()
    store.add_component(name, gen)
    return store


def _find_child_by_tag_attr(node, tag, attr_name, attr_value):
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if child.nodeName == tag.upper() and child.getAttribute(attr_name) == attr_value:
            return child
    return None
