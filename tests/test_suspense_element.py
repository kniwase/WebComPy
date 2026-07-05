from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.elements.generators import suspense
from webcompy.elements.types._suspense import SuspenseElement
from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY, HOST_PORT_KEY
from webcompy_server.ports import VirtualDOMNode
from webcompy_testing import FakeBrowserDOMPort, FakeBrowserFFIPort, FakeBrowserHostPort


class _DummyParent:
    def __init__(self, node=None):
        self._node = node or VirtualDOMNode("div")
        self._node.__webcompy_node__ = False
        self._node.__webcompy_prerendered_node__ = True

    def _get_node(self):
        return self._node

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self):
        return ()

    def _re_index_children(self, recursive):
        pass


@pytest.fixture
def suspense_scope():
    from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
    from webcompy_testing import FakeAsyncSchedulerPort

    scope = DIScope()
    scope.provide(ASYNC_SCHEDULER_PORT_KEY, FakeAsyncSchedulerPort())
    scope.provide(DOM_PORT_KEY, FakeBrowserDOMPort())
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    token = _active_di_scope.set(scope)
    yield scope
    _active_di_scope.reset(token)
    scope.dispose()


class TestSuspenseElement:
    def test_suspense_is_dynamic_element_subclass(self):
        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, "content"),
        )
        from webcompy.elements.types._dynamic import DynamicElement

        assert isinstance(el, DynamicElement)

    def test_init_stores_parameters(self):
        def fallback():
            return html.P({}, "loading")

        def children():
            return html.DIV({}, "content")

        def error_fb():
            return html.P({}, "error")

        el = SuspenseElement(
            fallback=fallback,
            children=children,
            error_fallback=error_fb,
            timeout=30.0,
        )
        assert el._fallback_generator is fallback
        assert el._children_generator is children
        assert el._error_fallback_generator is error_fb
        assert el._timeout == 30.0

    def test_children_generator_not_called_during_init(self):
        call_count = 0

        def children():
            nonlocal call_count
            call_count += 1
            return html.DIV({}, "content")

        SuspenseElement(fallback=lambda: html.P({}, "loading"), children=children)
        assert call_count == 0

    @pytest.mark.asyncio
    async def test_sync_children_render_immediately_without_fallback(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        parent = _DummyParent()

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({"id": "content"}, "hello"),
        )
        el._parent = parent
        el._node_idx = 0
        await el._render()

        assert len(el._children) > 0
        assert parent._node.childNodes.length > 0

    @pytest.mark.asyncio
    async def test_fallback_shown_when_async_children_pending(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        parent = _DummyParent()

        async def _dummy_coro():
            await asyncio.sleep(0)
            return html.DIV({}, "resolved")

        def children_generator():
            from webcompy.components._component import Component

            mock_component = MagicMock(spec=Component)
            mock_component._pending_async_template = _dummy_coro()
            mock_component._property = {"component_id": "test-cmp"}
            mock_component._children = []
            mock_component._node_idx = 0
            mock_component._mounted = None
            mock_component._parent = parent
            return html.DIV({}, mock_component)

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading..."),
            children=children_generator,
        )
        el._parent = parent
        el._node_idx = 0
        await el._render()

        assert len(el._children) > 0
        html_out = _render_to_html(parent._node)
        assert "loading" in html_out

    @pytest.mark.asyncio
    async def test_suspense_generator_creates_suspense_element(self):
        el = suspense(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, "content"),
        )
        assert isinstance(el, SuspenseElement)

    @pytest.mark.asyncio
    async def test_suspense_on_set_parent_noops(self):
        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, "content"),
        )
        parent = _DummyParent()
        el._parent = parent
        assert el._children == []

    @pytest.mark.asyncio
    async def test_remove_element_cancels_pending_tasks(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, "content"),
        )
        parent = _DummyParent()
        el._parent = parent
        el._node_idx = 0
        await el._render()

        task = asyncio.ensure_future(asyncio.sleep(10))
        el._pending_tasks.append(task)
        assert not task.done()

        el._remove_element(recursive=False, remove_node=False)
        await asyncio.sleep(0)
        assert task.cancelled()
        assert task not in el._pending_tasks

    def test_generate_fallback_returns_fallback_element(self):
        el = SuspenseElement(
            fallback=lambda: html.SPAN({}, "fallback text"),
            children=lambda: html.DIV({}, "content"),
        )
        parent = _DummyParent()
        el._parent = parent

        fallback = el._generate_fallback()
        assert len(fallback) == 1
        html_out = _render_to_html(parent._node)
        _ = html_out


def _render_to_html(node: VirtualDOMNode) -> str:
    from webcompy_server.ports._dom import ServerDOMPort

    port = ServerDOMPort()
    return port.render_html(node)
