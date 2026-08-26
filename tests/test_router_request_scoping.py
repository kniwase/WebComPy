from __future__ import annotations

import sys
import types

import pytest

from tests.conftest import MockHistoryPort
from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.components import define_component
from webcompy.elements import html
from webcompy.router import Router, RouterView
from webcompy.router._lazy import LazyComponentGenerator
from webcompy_server import configure_server_context


@define_component()
def ScopingRoot(context):
    return html.DIV({}, RouterView())


@define_component()
def ScopingPage(context):
    return html.DIV({}, "page")


class TestHooksAcrossRenderContexts:
    def test_hooks_registered_before_context_creation_fire_on_injected_router(self):
        hist = MockHistoryPort(mode="hash")
        router = Router(
            {"path": "/docs", "component": ScopingPage},
            history=hist,
            preload=False,
        )
        guarded: list[str] = []
        navigated: list[str] = []
        router.before_route_change.append(lambda frm, to: guarded.append(to))
        router.after_route_change.append(navigated.append)

        app = WebComPyApp(root_component=ScopingRoot, router=router, config=WebComPyAppConfig())
        configure_server_context(app)

        ctx = app.create_render_context()
        try:
            ctx._router.__set_path__("/docs", None)
        finally:
            ctx.dispose()

        assert guarded == ["/docs/"]
        assert navigated == ["/docs/"]


class TestLazyRegistrationAcrossRenderContexts:
    @pytest.mark.asyncio
    async def test_resolved_lazy_generator_registered_in_later_render_contexts(self):
        from webcompy.components._generator import ComponentStore
        from webcompy.di import DIScope
        from webcompy.di._keys import _COMPONENT_STORE_KEY

        scope0 = DIScope()
        store0 = ComponentStore()
        scope0.provide(_COMPONENT_STORE_KEY, store0)
        scope0.__enter__()
        try:

            @define_component()
            def LazyPage(context):
                return html.DIV({}, "lazy")
        finally:
            scope0.__exit__(None, None, None)
        assert "LazyPage" in store0.components, "generator must be registered at definition time (not deferred)"

        fake_module = types.ModuleType("req_scope_module")
        fake_module.LazyPage = LazyPage
        sys.modules["req_scope_module"] = fake_module

        lazy_gen = LazyComponentGenerator("req_scope_module:LazyPage", __file__)
        router = Router(
            {"path": "/docs", "component": lazy_gen},
            history=MockHistoryPort(mode="hash"),
            preload=True,
        )
        app = WebComPyApp(root_component=ScopingRoot, router=router, config=WebComPyAppConfig())
        configure_server_context(app)

        ctx1 = app.create_render_context("/docs")
        try:
            assert lazy_gen._resolved is LazyPage, "the automatic RouterView preload must resolve the lazy route"
            assert "LazyPage" in ctx1._component_store.components
        finally:
            ctx1.dispose()

        ctx2 = app.create_render_context("/docs")
        try:
            assert "LazyPage" in ctx2._component_store.components, (
                "a generator created in an earlier context must still register into the "
                "fresh store of a later render context (all generators are re-registered "
                "per context via the global generator registry)"
            )
        finally:
            ctx2.dispose()
        sys.modules.pop("req_scope_module", None)
