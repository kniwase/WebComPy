from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.di._keys import RPC_MIDDLEWARE_KEY
from webcompy.ports._keys import FETCH_MIDDLEWARE_KEY, FETCH_PORT_KEY
from webcompy.ports._middleware import FetchRequest, _MiddlewareFetchPort
from webcompy_server import configure_server_context


def _make_starlette_app() -> Starlette:
    async def handler(request):
        return JSONResponse({"data": "ok"})

    return Starlette(routes=[Route("/api/data", endpoint=handler)])


def _make_server_app() -> WebComPyApp:
    app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
    configure_server_context(app)
    app._server_fetch_port.configure(_make_starlette_app(), [])
    return app


class TestServerRenderContextMiddleware:
    @pytest.mark.asyncio
    async def test_registered_middleware_observes_request_and_bake_survives(self):
        app = _make_server_app()
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            port = ctx.di_scope.inject(FETCH_PORT_KEY)
            registry = ctx.di_scope.inject(FETCH_MIDDLEWARE_KEY)
            assert isinstance(port, _MiddlewareFetchPort)
            assert registry is not None

            seen: list[str] = []

            async def spy(request: FetchRequest, next):  # type: ignore[name-defined]
                seen.append(request.url)
                return await next(request)

            registry.use(spy)

            response = await port.fetch("/api/data")
            assert response.status_code == 200
            assert seen == ["/api/data"]

            transfer = port.get_transfer_data()
            assert "/api/data" in transfer
        finally:
            ctx.dispose()

    def test_registries_are_isolated_between_contexts(self):
        app = _make_server_app()
        ctx1 = app.create_render_context("/", initial_theme=None)
        ctx2 = app.create_render_context("/", initial_theme=None)
        try:
            reg1 = ctx1.di_scope.inject(FETCH_MIDDLEWARE_KEY)
            reg2 = ctx2.di_scope.inject(FETCH_MIDDLEWARE_KEY)
            rpc1 = ctx1.di_scope.inject(RPC_MIDDLEWARE_KEY)
            rpc2 = ctx2.di_scope.inject(RPC_MIDDLEWARE_KEY)
            assert reg1 is not reg2
            assert rpc1 is not rpc2

            async def mw(request: FetchRequest, next):  # type: ignore[name-defined]
                return await next(request)

            reg1.use(mw)
            assert reg1.middlewares == (mw,)
            assert reg2.middlewares == ()
        finally:
            ctx1.dispose()
            ctx2.dispose()
