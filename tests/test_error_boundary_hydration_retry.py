from __future__ import annotations

import pytest

from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.elements.types._error_boundary import ErrorBoundaryElement
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, DOM_PORT_KEY, FFI_PORT_KEY, HOST_PORT_KEY
from webcompy_server.ports import VirtualDOMNode
from webcompy_testing import FakeAsyncSchedulerPort, FakeBrowserDOMPort, FakeBrowserFFIPort, FakeBrowserHostPort


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
def hydration_scope():
    scope = DIScope()
    scope.provide(ASYNC_SCHEDULER_PORT_KEY, FakeAsyncSchedulerPort())
    scope.provide(DOM_PORT_KEY, FakeBrowserDOMPort())
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    token = _active_di_scope.set(scope)
    yield scope
    _active_di_scope.reset(token)
    scope.dispose()


def _child_nodes(node):
    return [node.childNodes[i] for i in range(node.childNodes.length)]


class TestHydrationRetry:
    @pytest.mark.asyncio
    async def test_hydration_adopts_ssr_fallback_and_retries(self, hydration_scope):
        parent_node = VirtualDOMNode("div")
        parent_node.__webcompy_node__ = False
        parent_node.__webcompy_prerendered_node__ = True
        fallback_dom = VirtualDOMNode("div")
        fallback_dom.__webcompy_prerendered_node__ = True
        fallback_dom.setAttribute("data-webcompy-error-fallback", "")
        parent_node.appendChild(fallback_dom)
        parent = _DummyParent(parent_node)

        boundary = ErrorBoundaryElement(
            children=lambda: html.DIV({"data-testid": "hydrated-child"}),
            fallback=lambda e, r: html.DIV({"data-testid": "ssr-fallback"}),
        )
        boundary._parent = parent
        boundary._node_idx = 0
        boundary._hydrate_node()

        assert boundary._in_fallback
        assert boundary._children[0]._node_cache is fallback_dom

        scheduler = hydration_scope.inject(ASYNC_SCHEDULER_PORT_KEY)
        assert len(scheduler._coroutines) == 1
        await scheduler.drain()

        assert not boundary._in_fallback
        assert boundary._error is None
        nodes = _child_nodes(parent_node)
        assert len(nodes) == 1
        assert nodes[0].getAttribute("data-testid") == "hydrated-child"
        assert nodes[0].getAttribute("data-webcompy-error-fallback") is None

    @pytest.mark.asyncio
    async def test_hydration_retry_persistent_failure_settles_into_fallback(self, hydration_scope):
        parent_node = VirtualDOMNode("div")
        parent_node.__webcompy_node__ = False
        parent_node.__webcompy_prerendered_node__ = True
        fallback_dom = VirtualDOMNode("div")
        fallback_dom.__webcompy_prerendered_node__ = True
        fallback_dom.setAttribute("data-webcompy-error-fallback", "")
        parent_node.appendChild(fallback_dom)
        parent = _DummyParent(parent_node)

        def crashing_children():
            raise RuntimeError("still broken")

        boundary = ErrorBoundaryElement(
            children=crashing_children,
            fallback=lambda e, r: html.DIV({"data-testid": "ssr-fallback"}),
        )
        boundary._parent = parent
        boundary._node_idx = 0
        boundary._hydrate_node()

        assert boundary._in_fallback

        scheduler = hydration_scope.inject(ASYNC_SCHEDULER_PORT_KEY)
        await scheduler.drain()

        assert boundary._in_fallback
        assert len(boundary._children) == 1

    @pytest.mark.asyncio
    async def test_hydration_without_marker_hydrates_children_normally(self, hydration_scope):
        parent_node = VirtualDOMNode("div")
        parent_node.__webcompy_node__ = False
        parent_node.__webcompy_prerendered_node__ = True
        child_dom = VirtualDOMNode("div")
        child_dom.__webcompy_prerendered_node__ = True
        parent_node.appendChild(child_dom)
        parent = _DummyParent(parent_node)

        boundary = ErrorBoundaryElement(
            children=lambda: html.DIV({"data-testid": "hydrated-child"}),
            fallback=lambda e, r: html.DIV({"data-testid": "ssr-fallback"}),
        )
        boundary._parent = parent
        boundary._node_idx = 0
        boundary._hydrate_node()

        assert not boundary._in_fallback
        assert boundary._children[0]._node_cache is child_dom
        scheduler = hydration_scope.inject(ASYNC_SCHEDULER_PORT_KEY)
        assert len(scheduler._coroutines) == 1
        await scheduler.drain()

    @pytest.mark.asyncio
    async def test_server_engagement_marks_fallback_root(self, hydration_scope):
        parent = _DummyParent()
        boundary = ErrorBoundaryElement(
            children=lambda: html.DIV({}, "content"),
            fallback=lambda e, r: html.DIV({"data-testid": "marked-fallback"}),
        )
        boundary._parent = parent
        boundary._node_idx = 0
        await boundary._engage(RuntimeError("ssr error"))

        assert boundary._in_fallback
        node = boundary._children[0]._node_cache
        assert node.getAttribute("data-webcompy-error-fallback") == ""
