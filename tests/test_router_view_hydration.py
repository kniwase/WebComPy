from __future__ import annotations

import pytest

from tests.conftest import MockHistoryPort
from tests.test_hydration_preservation_helpers import (
    make_prerendered_parent,
    prerendered_div,
)
from webcompy.components import ComponentContext, define_component
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements import html
from webcompy.router import Router, RouterView

pytestmark = pytest.mark.usefixtures("fake_browser_full")


@define_component()
def SyncHydrationPage(context: ComponentContext[None]):
    return html.DIV({"data-testid": "sync-page"}, "sync-content")


@define_component()
async def AsyncHydrationPage(context: ComponentContext[None]):
    return html.DIV({"data-testid": "async-page"}, "async-content")


def _make_router(path: str) -> Router:
    hist = MockHistoryPort(mode="history")
    router = Router(
        {"path": "/sync", "component": SyncHydrationPage},
        {"path": "/async", "component": AsyncHydrationPage},
        history=hist,
        preload=False,
    )
    hist.navigate(path, None)
    return router


def _hydrate_router_view(path: str):
    from webcompy.components._component import HeadPropsStore
    from webcompy.components._generator import ComponentStore
    from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
    from webcompy.di._scope import _active_di_scope

    router = _make_router(path)
    scope = _active_di_scope.get(None)
    assert scope is not None
    scope.provide(_ROUTER_KEY, router)
    scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
    scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
    from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY
    from webcompy_testing import FakeCustomElementPort

    scope.provide(CUSTOM_ELEMENT_PORT_KEY, FakeCustomElementPort())

    view = RouterView()
    view._parent = None  # set below
    return view


def _attach(view, parent):
    view._parent = parent
    view._node_idx = 0
    parent._children = [view]


def _page_instance(view):
    boundary = view._children[0]
    return boundary._children[0]


@pytest.mark.asyncio
async def test_sync_route_page_ssr_nodes_survive_hydration(eager_scheduler):
    view = _hydrate_router_view("/sync")
    content_ssr = prerendered_div("sync-content")
    content_ssr.setAttribute("data-testid", "sync-page")
    page_ssr = _ssr_custom_element("sync-hydration-page", content_ssr)
    parent = make_prerendered_parent(page_ssr)

    _attach(view, parent)
    view._hydrate_node()
    assert page_ssr.parentNode is parent._node_cache

    await view._render()
    await eager_scheduler.await_pending()

    assert page_ssr.parentNode is parent._node_cache
    assert parent._node_cache.childNodes[0] is page_ssr
    assert page_ssr.childNodes[0] is content_ssr


@pytest.mark.asyncio
async def test_async_route_page_ssr_nodes_survive_hydration(eager_scheduler):
    view = _hydrate_router_view("/async")
    content_ssr = prerendered_div("async-content")
    content_ssr.setAttribute("data-testid", "async-page")
    page_ssr = _ssr_custom_element("async-hydration-page", content_ssr)
    parent = make_prerendered_parent(page_ssr)

    _attach(view, parent)
    view._hydrate_node()
    assert page_ssr.parentNode is parent._node_cache

    await view._render()
    await eager_scheduler.await_pending()

    assert page_ssr.parentNode is parent._node_cache
    assert parent._node_cache.childNodes[0] is page_ssr
    assert page_ssr.childNodes[0] is content_ssr


@pytest.mark.asyncio
async def test_sync_route_page_renders_exactly_once(eager_scheduler, monkeypatch):
    from webcompy.components._component import Component

    view = _hydrate_router_view("/sync")
    parent = make_prerendered_parent(_ssr_custom_element("sync-hydration-page", prerendered_div("sync-content")))
    _attach(view, parent)

    counters: dict[int, int] = {}

    original = Component._render

    async def counted(self, *args, **kwargs):
        counters[id(self)] = counters.get(id(self), 0) + 1
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(Component, "_render", counted)

    view._hydrate_node()
    await view._render()
    await eager_scheduler.await_pending()

    page = _page_instance(view)
    assert counters.get(id(page), 0) == 1


def _ssr_custom_element(tag: str, *children):
    from webcompy_testing import FakeDOMNode

    node = FakeDOMNode(tag)
    node.__webcompy_prerendered_node__ = True
    for child in children:
        node.appendChild(child)
    return node
