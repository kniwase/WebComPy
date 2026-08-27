from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from webcompy.components import define_component
from webcompy.components._component import _active_app_context, _set_app_instance
from webcompy.elements import ErrorBoundary, html
from webcompy.elements.types._error_boundary import ErrorBoundaryElement
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy_server.ports import VirtualDOMEvent
from webcompy_testing import TestRenderer


def _use_fake_app(fake_ctx):
    token = _active_app_context.set(None)
    _set_app_instance(fake_ctx)
    return token


def _release_fake_app(token):
    _set_app_instance(None)
    _active_app_context.reset(token)


def _find_element_by_testid(root, testid: str):
    attrs = getattr(root, "_attrs", None) or {}
    if attrs.get("data-testid") == testid:
        return root
    for child in getattr(root, "_children", None) or []:
        found = _find_element_by_testid(child, testid)
        if found is not None:
            return found
    return None


def _find_boundary(root) -> ErrorBoundaryElement | None:
    if isinstance(root, ErrorBoundaryElement):
        return root
    for child in getattr(root, "_children", None) or []:
        found = _find_boundary(child)
        if found is not None:
            return found
    return None


class TestSyncEventHandlerErrors:
    def test_sync_handler_error_reaches_global_handler_without_dom_change(self):
        received: list[Exception] = []
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=received.append))

        @define_component()
        def TestRoot(context):
            def boom(_):
                raise RuntimeError("sync event boom")

            return html.DIV(
                {},
                html.BUTTON({"data-testid": "btn", "@click": boom}, "boom"),
                html.SPAN({"data-testid": "unchanged"}, "still here"),
            )

        with TestRenderer.render(TestRoot) as result:
            btn = result.find_by_attribute("data-testid", "btn")
            assert btn is not None
            html_before = result.to_html()
            token = _use_fake_app(fake_ctx)
            try:
                btn.dispatchEvent(VirtualDOMEvent("click"))
            finally:
                _release_fake_app(token)
            assert len(received) == 1
            assert str(received[0]) == "sync event boom"
            assert result.to_html() == html_before

    def test_sync_handler_error_engages_catch_events_boundary(self):
        @define_component()
        def TestRoot(context):
            def boom(_):
                raise RuntimeError("caught event boom")

            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: html.BUTTON({"data-testid": "btn", "@click": boom}, "boom"),
                    fallback=lambda e, r: html.DIV({"data-testid": "event-fallback"}, str(e)),
                    catch_events=True,
                ),
            )

        with TestRenderer.render(TestRoot) as result:
            btn = result.find_by_attribute("data-testid", "btn")
            assert btn is not None
            btn.dispatchEvent(VirtualDOMEvent("click"))
            assert result.find_by_attribute("data-testid", "event-fallback") is not None
            assert result.find_by_text("caught event boom") is not None
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert boundary._in_fallback

    def test_sync_handler_error_skips_boundary_without_catch_events(self):
        received: list[Exception] = []
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=received.append))

        @define_component()
        def TestRoot(context):
            def boom(_):
                raise RuntimeError("uncaught event boom")

            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: html.BUTTON({"data-testid": "btn", "@click": boom}, "boom"),
                    fallback=lambda e, r: html.DIV({"data-testid": "event-fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(TestRoot) as result:
            btn = result.find_by_attribute("data-testid", "btn")
            assert btn is not None
            token = _use_fake_app(fake_ctx)
            try:
                btn.dispatchEvent(VirtualDOMEvent("click"))
            finally:
                _release_fake_app(token)
            assert result.find_by_attribute("data-testid", "event-fallback") is None
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert not boundary._in_fallback
            assert len(received) == 1
            assert str(received[0]) == "uncaught event boom"


class TestAsyncEventHandlerErrors:
    @pytest.mark.asyncio
    async def test_async_handler_error_reaches_global_handler(self):
        received: list[Exception] = []
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=received.append))

        @define_component()
        def TestRoot(context):
            async def boom(_):
                await asyncio.sleep(0)
                raise RuntimeError("async event boom")

            return html.DIV({}, html.BUTTON({"data-testid": "btn", "@click": boom}, "boom"))

        with TestRenderer.render(TestRoot) as result:
            btn = result.find_by_attribute("data-testid", "btn")
            assert btn is not None
            token = _use_fake_app(fake_ctx)
            try:
                btn.dispatchEvent(VirtualDOMEvent("click"))
                scheduler = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
                await scheduler.drain()
            finally:
                _release_fake_app(token)
            assert len(received) == 1
            assert str(received[0]) == "async event boom"

    @pytest.mark.asyncio
    async def test_async_handler_error_engages_catch_events_boundary(self):
        @define_component()
        def TestRoot(context):
            async def boom(_):
                await asyncio.sleep(0)
                raise RuntimeError("async caught boom")

            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: html.BUTTON({"data-testid": "btn", "@click": boom}, "boom"),
                    fallback=lambda e, r: html.DIV({"data-testid": "event-fallback"}, str(e)),
                    catch_events=True,
                ),
            )

        with TestRenderer.render(TestRoot) as result:
            btn = result.find_by_attribute("data-testid", "btn")
            assert btn is not None
            btn.dispatchEvent(VirtualDOMEvent("click"))
            scheduler = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.drain()
            assert result.find_by_attribute("data-testid", "event-fallback") is not None
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert boundary._in_fallback


class TestProxyLifecycle:
    def test_proxy_destroyed_on_element_removal(self):
        @define_component()
        def TestRoot(context):
            def noop(_):
                return None

            return html.DIV({}, html.BUTTON({"data-testid": "btn", "@click": noop}, "ok"))

        with TestRenderer.render(TestRoot) as result:
            btn = _find_element_by_testid(result._instance, "btn")
            assert btn is not None
            proxy = btn._event_handlers_added["click"]
            btn._remove_element()
            assert proxy.destroy.called
