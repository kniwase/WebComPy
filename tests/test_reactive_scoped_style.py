from __future__ import annotations

import pytest

from webcompy.components._generator import ComponentGenerator, ComponentStore
from webcompy.components._reactive_scoped_style import (
    ReactiveScopedStyle,
    reactive_scoped_style,
)
from webcompy.exception import WebComPyException
from webcompy.signal import Signal


def _noop(ctx):
    pass


class TestReactiveScopedStyleBasics:
    def test_create_with_constant_dict(self):
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        assert isinstance(style, ReactiveScopedStyle)

    def test_async_function_rejected(self):
        async def f():
            return {".x": {"color": "red"}}

        with pytest.raises(TypeError, match="synchronous"):
            reactive_scoped_style(f)

    def test_dict_computed_returns_dict(self):
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        style._bind("test-cid")
        assert style.dict_computed.value == {".x": {"color": "red"}}

    def test_dict_computed_tracks_signal(self):
        color = Signal("blue")
        style = reactive_scoped_style(lambda: {".x": {"color": color.value}})
        style._bind("test-cid")
        assert style.dict_computed.value == {".x": {"color": "blue"}}
        color.value = "red"
        assert style.dict_computed.value == {".x": {"color": "red"}}

    def test_dict_computed_unbound_raises(self):
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        with pytest.raises(WebComPyException, match="not bound"):
            _ = style.dict_computed

    def test_css_computed_unbound_raises(self):
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        with pytest.raises(WebComPyException, match="not bound"):
            _ = style.css_computed


class TestReactiveScopedStyleRenderCss:
    def test_render_simple_selector(self):
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        style._bind("abc")
        out = style.render_css("abc")
        assert "@layer webcompy-scope" in out
        assert ".x[webcompy-cid-abc]" in out
        assert "color: red" in out

    def test_render_pseudo_class(self):
        style = reactive_scoped_style(lambda: {".btn": {"color": "blue", ":hover": {"background": "yellow"}}})
        style._bind("c1")
        out = style.render_css("c1")
        assert ".btn[webcompy-cid-c1]" in out
        assert ".btn[webcompy-cid-c1]:hover" in out
        assert "color: blue" in out
        assert "background: yellow" in out

    def test_render_combinator(self):
        style = reactive_scoped_style(lambda: {".menu": {"> li": {"color": "red"}}})
        style._bind("c2")
        out = style.render_css("c2")
        assert ".menu[webcompy-cid-c2] > li" in out

    def test_render_at_rule(self):
        style = reactive_scoped_style(lambda: {"@media (max-width: 768px)": {".btn": {"color": "red"}}})
        style._bind("c3")
        out = style.render_css("c3")
        assert "@media (max-width: 768px)" in out
        assert ".btn[webcompy-cid-c3]" in out
        assert "color: red" in out

    def test_render_keyframes(self):
        style = reactive_scoped_style(lambda: {"@keyframes fade": {"from": {"opacity": "0"}, "to": {"opacity": "1"}}})
        style._bind("c4")
        out = style.render_css("c4")
        assert "@keyframes fade" in out
        assert "opacity: 0" in out
        assert "opacity: 1" in out

    def test_render_empty_returns_empty(self):
        style = reactive_scoped_style(lambda: {})
        style._bind("c5")
        assert style.render_css("c5") == ""

    def test_render_signal_change_updates_css(self):
        color = Signal("blue")
        style = reactive_scoped_style(lambda: {".x": {"color": color.value}})
        style._bind("c6")
        first = style.render_css("c6")
        assert "color: blue" in first
        color.value = "red"
        second = style.render_css("c6")
        assert "color: red" in second

    def test_render_consistent_with_static_path_for_constant_dict(self):
        def _noop2(ctx):
            pass

        gen = ComponentGenerator("CompareComp", _noop2)
        gen.scoped_style = {".btn": {"color": "blue", ":hover": {"background": "yellow"}}}
        static = gen.scoped_style

        style = reactive_scoped_style(lambda: {".btn": {"color": "blue", ":hover": {"background": "yellow"}}})
        style._bind(gen._id)
        reactive = style.render_css(gen._id)

        assert static == reactive

    def test_double_bind_same_cid_idempotent(self):
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        style._bind("c7")
        c1 = style.css_computed
        style._bind("c7")
        c2 = style.css_computed
        assert c1 is c2

    def test_rebind_different_cid_raises(self):
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        style._bind("c8")
        with pytest.raises(WebComPyException, match="different component"):
            style._bind("c9")


class TestGeneratorReactiveStylesTracking:
    def test_generator_starts_with_empty_reactive_styles(self):
        gen = ComponentGenerator("EmptyComp", _noop)
        assert gen._reactive_styles == []

    def test_appending_via_use_method(self):
        from webcompy.components._libs import Context

        gen = ComponentGenerator("WithStyle", _noop)
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        context = Context(
            None,
            {},
            "WithStyle",
            lambda: "",
            lambda: {},
            lambda _: None,
            lambda _, __: None,
            generator=gen,
        )
        context.use_reactive_scoped_style(style)
        assert gen._reactive_styles == [style]
        assert style._cid == gen._id

    def test_double_registration_with_same_style_instance_is_noop(self):
        from webcompy.components._libs import Context

        gen = ComponentGenerator("DedupComp", _noop)
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        context = Context(
            None,
            {},
            "DedupComp",
            lambda: "",
            lambda: {},
            lambda _: None,
            lambda _, __: None,
            generator=gen,
        )
        context.use_reactive_scoped_style(style)
        context.use_reactive_scoped_style(style)
        context.use_reactive_scoped_style(style)
        assert gen._reactive_styles == [style]
        assert gen._reactive_styles.count(style) == 1

    def test_subscription_disposed_on_before_destroy(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._hooks import _active_component_context
        from webcompy.components._libs import Context
        from webcompy.di._scope import DIScope
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.testing._ports import FakeBrowserDOMPort

        gen = ComponentGenerator("DestroyComp", _noop)
        style = reactive_scoped_style(lambda: {".x": {"color": "blue"}})
        context = Context(
            None,
            {},
            "DestroyComp",
            lambda: "",
            lambda: {},
            lambda _: None,
            lambda _, __: None,
            generator=gen,
        )

        port = FakeBrowserDOMPort()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)

        di_token = _active_component_context.set(context)  # type: ignore[arg-type]
        from webcompy.di._scope import _active_di_scope

        di_scope_token = _active_di_scope.set(scope)
        try:
            context.use_reactive_scoped_style(style)
            consumer_count_before = _count_consumers(style._css_computed)
            assert consumer_count_before == 1

            hooks = context.__get_lifecyclehooks__()
            assert "on_before_destroy" in hooks
            hooks["on_before_destroy"]()

            consumer_count_after = _count_consumers(style._css_computed)
            assert consumer_count_after == 0
        finally:
            _active_di_scope.reset(di_scope_token)
            _active_component_context.reset(di_token)

    def test_use_outside_generator_raises(self):
        from webcompy.components._libs import Context

        context = Context(
            None,
            {},
            "NoGen",
            lambda: "",
            lambda: {},
            lambda _: None,
            lambda _, __: None,
        )
        style = reactive_scoped_style(lambda: {".x": {"color": "red"}})
        with pytest.raises(WebComPyException, match="@define_component"):
            context.use_reactive_scoped_style(style)

    def test_use_rejects_non_reactive_scoped_style(self):
        from webcompy.components._libs import Context

        gen = ComponentGenerator("Rejects", _noop)
        context = Context(
            None,
            {},
            "Rejects",
            lambda: "",
            lambda: {},
            lambda _: None,
            lambda _, __: None,
            generator=gen,
        )
        with pytest.raises(WebComPyException, match="ReactiveScopedStyle"):
            context.use_reactive_scoped_style("not a style")  # type: ignore[arg-type]


class TestGeneratorReactiveStylesIntegration:
    def test_multiple_reactive_styles_per_generator(self):
        gen = ComponentGenerator("MultiStyle", _noop)
        s1 = reactive_scoped_style(lambda: {".a": {"color": "red"}})
        s2 = reactive_scoped_style(lambda: {".b": {"color": "blue"}})
        s1._bind(gen._id)
        s2._bind(gen._id)
        gen._reactive_styles.extend([s1, s2])
        assert len(gen._reactive_styles) == 2
        out1 = s1.render_css(gen._id)
        out2 = s2.render_css(gen._id)
        assert ".a" in out1 and ".b" not in out1
        assert ".b" in out2 and ".a" not in out2


class TestHeadElementBrowserPath:
    @pytest.mark.asyncio
    async def test_reactive_style_injected_into_head(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.testing._ports import FakeBrowserDOMPort

        gen = ComponentGenerator("RxComp", _noop)
        style = reactive_scoped_style(lambda: {".dyn": {"color": "red"}})
        style._bind(gen._id)
        gen._reactive_styles.append(style)

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        store.add_component("RxComp", gen)
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

            rx_attr = f"{gen._id}-0"
            rx_el = _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid-rx", rx_attr)
            assert rx_el is not None
            assert "color: red" in (rx_el.textContent or "")
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_signal_change_updates_textContent(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._hooks import _active_component_context
        from webcompy.components._libs import Context
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.testing._ports import FakeBrowserDOMPort

        gen = ComponentGenerator("SigComp", _noop)
        color = Signal("blue")
        style = reactive_scoped_style(lambda: {".dyn": {"color": color.value}})

        context = Context(
            None,
            {},
            "SigComp",
            lambda: "",
            lambda: {},
            lambda _: None,
            lambda _, __: None,
            generator=gen,
        )

        port = FakeBrowserDOMPort()
        store = ComponentStore()
        store.add_component("SigComp", gen)
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        di_token = _active_di_scope.set(scope)
        ctx_token = _active_component_context.set(context)
        try:
            context.use_reactive_scoped_style(style)

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


class TestHeadElementSSRPath:
    def test_ssr_emits_reactive_style_element(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "server")

        from webcompy.components._component import HeadPropsStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.ports._server._dom import ServerDOMPort

        gen = ComponentGenerator("SsrComp", _noop)
        style = reactive_scoped_style(lambda: {".dyn": {"color": "red"}})
        style._bind(gen._id)
        gen._reactive_styles.append(style)

        port = ServerDOMPort()
        store = ComponentStore()
        store.add_component("SsrComp", gen)
        head_props = HeadPropsStore()

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)

        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            html = head_element.get_head_content_html()
            assert "data-webcompy-cid-rx" in html
            assert ".dyn[webcompy-cid-" in html
            assert "color: red" in html
        finally:
            _active_di_scope.reset(token)


def _find_child_by_tag_attr(node, tag, attr_name, attr_value):
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if child.nodeName == tag.upper() and child.getAttribute(attr_name) == attr_value:
            return child
    return None


def _count_consumers(producer: object) -> int:
    count = 0
    edge = getattr(producer, "consumers", None)
    while edge is not None:
        count += 1
        edge = edge.next_consumer
    return count
