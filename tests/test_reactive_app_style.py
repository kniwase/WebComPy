from __future__ import annotations

import pytest

from webcompy.app.styles import reactive_block, reactive_style
from webcompy.signal import Signal


class TestReactiveStyleHelper:
    def test_static_string_value(self):
        result = reactive_style(":root", {"--x": "red"}).value
        assert result == ":root {\n  --x: red;\n}"

    def test_multiple_vars(self):
        result = reactive_style(":root", {"--x": "red", "--y": "blue"}).value
        assert result == ":root {\n  --x: red;\n  --y: blue;\n}"

    def test_signal_value(self):
        sig = Signal("red")
        result = reactive_style(":root", {"--x": sig}).value
        assert "--x: red" in result
        sig.value = "blue"
        result = reactive_style(":root", {"--x": sig}).value
        assert "--x: blue" in result

    def test_callable_value(self):
        def _get():
            return "from_callable"

        result = reactive_style(":root", {"--x": _get}).value
        assert "--x: from_callable" in result

    def test_mixed_value_types(self):
        sig = Signal("dynamic")
        result = reactive_style(
            ":root",
            {"--a": "static", "--b": sig, "--c": lambda: "callable"},
        ).value
        assert "--a: static" in result
        assert "--b: dynamic" in result
        assert "--c: callable" in result

    def test_signal_change_triggers_recompute(self):
        sig = Signal("first")
        cs = reactive_style(":root", {"--x": sig})
        assert "--x: first" in cs.value
        sig.value = "second"
        assert "--x: second" in cs.value

    def test_empty_vars_returns_empty_string(self):
        assert reactive_style(":root", {}).value == ""

    def test_callable_returning_empty_string(self):
        def _get():
            return ""

        result = reactive_style(":root", {"--x": _get}).value
        assert "--x" in result
        assert ";" in result


class TestReactiveBlockHelper:
    def test_static_string(self):
        result = reactive_block("body", "color: red;").value
        assert result == "body {\ncolor: red;\n}"

    def test_signal_value_is_wrapped_verbatim(self):
        sig = Signal("red")
        result = reactive_block("body", sig).value
        assert "color:" not in result
        assert result == "body {\nred\n}"

    def test_callable_value(self):
        result = reactive_block("body", lambda: "color: blue;").value
        assert result == "body {\ncolor: blue;\n}"

    def test_signal_change_triggers_recompute(self):
        sig = Signal("first")
        cb = reactive_block("body", sig)
        assert "first" in cb.value
        sig.value = "second"
        assert "second" in cb.value

    def test_empty_string_content(self):
        result = reactive_block("body", "").value
        assert result == "body {\n\n}"


class TestHeadElementAppStyle:
    def test_append_style_static_string(self):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_server.ports._dom import ServerDOMPort

        port = ServerDOMPort()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            head_element.append_style(".my-class { color: red; }")
            html = head_element.get_head_content_html()
            assert 'data-webcompy-dynamic="0"' in html
            assert ".my-class { color: red; }" in html
        finally:
            _active_di_scope.reset(token)

    def test_append_style_computed_ssr_value(self):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_server.ports._dom import ServerDOMPort

        port = ServerDOMPort()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            sig = Signal("blue")
            cs = reactive_style(":root", {"--color": sig})
            head_element.append_style(cs)
            html = head_element.get_head_content_html()
            assert "--color: blue" in html

            sig.value = "red"
            html = head_element.get_head_content_html()
            assert "--color: red" in html
        finally:
            _active_di_scope.reset(token)

    def test_multiple_appends_separate_elements(self):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_server.ports._dom import ServerDOMPort

        port = ServerDOMPort()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            head_element.append_style(".a { color: red; }")
            head_element.append_style(".b { color: blue; }")
            head_element.append_style(".c { color: green; }")
            html = head_element.get_head_content_html()
            assert 'data-webcompy-dynamic="0"' in html
            assert 'data-webcompy-dynamic="1"' in html
            assert 'data-webcompy-dynamic="2"' in html
            assert ".a" in html
            assert ".b" in html
            assert ".c" in html
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_browser_path_injects_dynamic_style(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            head_element.append_style(".dyn { color: red; }")
            await head_element._render()

            head_el = port.query_selector("head")
            assert head_el is not None
            dyn_el = _find_child_by_tag_attr(head_el, "style", "data-webcompy-dynamic", "0")
            assert dyn_el is not None
            assert ".dyn" in (dyn_el.textContent or "")
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_signal_change_updates_dynamic_style(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            sig = Signal("blue")
            cs = reactive_style(":root", {"--x": sig})
            head_element.append_style(cs)
            await head_element._render()

            head_el = port.query_selector("head")
            dyn_el = _find_child_by_tag_attr(head_el, "style", "data-webcompy-dynamic", "0")
            assert dyn_el is not None
            assert "--x: blue" in (dyn_el.textContent or "")

            sig.value = "red"
            assert "--x: red" in (dyn_el.textContent or "")
        finally:
            _active_di_scope.reset(token)

    def test_cleanup_disposes_style_subscriptions(self, monkeypatch):
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            sig = Signal("blue")
            cs = reactive_style(":root", {"--x": sig})
            head_element.append_style(cs)

            consumer_count_before = _count_consumers(cs)
            assert consumer_count_before == 1
            assert len(head_element._style_callbacks) == 1

            head_element._cleanup_consumers()

            assert len(head_element._style_callbacks) == 0
            consumer_count_after = _count_consumers(cs)
            assert consumer_count_after == 0

            sig.value = "red"
            assert _count_consumers(cs) == 0
        finally:
            _active_di_scope.reset(token)

    def test_cleanup_removes_orphaned_style_elements(self, monkeypatch):
        """Regression test for PR #178 sixth-round review: when the render
        context is disposed, ``_cleanup_consumers`` MUST also remove any
        ``<style data-webcompy-cid>`` and ``<style data-webcompy-cid-rx>``
        elements that the head element emitted. Without this, the elements
        accumulate in the document <head> across app lifecycle events
        (re-renders, navigation, theme toggles that trigger re-renders)."""
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        import asyncio

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import (
            ComponentGenerator,
            ComponentStore,
        )
        from webcompy.components._reactive_scoped_style import (
            reactive_scoped_style,
        )
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head_props = HeadPropsStore()
        store = ComponentStore()

        def _noop(_: object) -> None:
            pass

        gen_static = ComponentGenerator("StaticCid", _noop)
        gen_static._style = {".x": {"color": "red"}}
        store.add_component("StaticCid", gen_static)

        gen_rx = ComponentGenerator("ReactiveCid", _noop)
        rx_style = reactive_scoped_style(lambda: {".y": {"color": "blue"}})
        rx_style._bind(gen_rx._id)
        gen_rx._reactive_styles.append(rx_style)
        store.add_component("ReactiveCid", gen_rx)

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, store)
        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            asyncio.run(head_element._render())

            head_el = port.query_selector("head")
            assert head_el is not None
            cid_static_el = _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid", gen_static._id)
            assert cid_static_el is not None
            cid_rx_attr = f"{gen_rx._id}-0"
            cid_rx_el = _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid-rx", cid_rx_attr)
            assert cid_rx_el is not None

            head_element._cleanup_consumers()

            head_el = port.query_selector("head")
            assert head_el is not None
            cid_static_after = _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid", gen_static._id)
            assert cid_static_after is None
            cid_rx_after = _find_child_by_tag_attr(head_el, "style", "data-webcompy-cid-rx", cid_rx_attr)
            assert cid_rx_after is None
        finally:
            _active_di_scope.reset(token)

    def test_dynamic_style_callback_resolves_dom_at_registration(self, monkeypatch):
        """Regression test for PR #178 review: the _subscribe_callback
        registered by ``append_style`` MUST resolve the DOM port once at
        registration time (not on every signal update) so that a late
        callback firing after the render context is disposed does not
        raise ``InjectionError``."""
        monkeypatch.setattr("webcompy.utils.ENVIRONMENT", "pyscript")

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements._head import HeadElement
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing._ports import FakeBrowserDOMPort

        port = FakeBrowserDOMPort()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(DOM_PORT_KEY, port)
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        token = _active_di_scope.set(scope)
        try:
            head_element = HeadElement(head_props)
            sig = Signal("blue")
            cs = reactive_style(":root", {"--x": sig})
            head_element.append_style(cs)
        finally:
            _active_di_scope.reset(token)

        assert len(head_element._style_callbacks) == 1
        sig.value = "red"


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
