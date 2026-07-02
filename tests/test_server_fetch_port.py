from __future__ import annotations

from typing import Any

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from webcompy.exception import WebComPyException
from webcompy.ports._fetch import FetchPort, Response
from webcompy_server.ports._fetch import ServerFetchPort


class TestIsSelfSiteUrl:
    def test_default_fetch_port_returns_false(self):
        class CustomPort(FetchPort):
            async def fetch(self, *args: Any, **kwargs: Any) -> Response:
                raise NotImplementedError

        port = CustomPort()
        assert port.is_self_site_url("/api/data") is False
        assert port.is_self_site_url("https://example.com") is False

    def test_absolute_path_is_self_site(self):
        port = ServerFetchPort()
        assert port.is_self_site_url("/api/data") is True

    def test_relative_path_is_self_site(self):
        port = ServerFetchPort()
        assert port.is_self_site_url("./data") is True
        assert port.is_self_site_url("../parent") is True

    def test_external_https_is_not_self_site(self):
        port = ServerFetchPort()
        assert port.is_self_site_url("https://api.example.com/data") is False

    def test_external_http_is_not_self_site(self):
        port = ServerFetchPort()
        assert port.is_self_site_url("http://localhost:3000/api") is False

    def test_protocol_relative_url_is_not_self_site(self):
        port = ServerFetchPort()
        assert port.is_self_site_url("//cdn.example.com/file") is False

    def test_empty_string_is_not_self_site(self):
        port = ServerFetchPort()
        assert port.is_self_site_url("") is False


class TestServerFetchPortConfigure:
    def test_configure_creates_self_site_client(self):
        port = ServerFetchPort()
        assert port._self_site_client is None
        assert port._asgi_app is None

        app = Starlette(routes=[])
        port.configure(app, blocked_paths=["/"])

        assert port._self_site_client is not None
        assert port._asgi_app is not None

    def test_configure_sets_blocked_paths(self):
        port = ServerFetchPort()
        app = Starlette(routes=[])
        port.configure(app, blocked_paths=["/", "/admin"])

        assert port._blocked_paths == ["/", "/admin"]

    def test_configure_sets_base_url(self):
        port = ServerFetchPort()
        app = Starlette(routes=[])
        port.configure(app, base_url="/myapp/")

        assert port._base_url == "/myapp/"

    def test_configure_raises_on_second_call(self):
        port = ServerFetchPort()
        app = Starlette(routes=[])
        port.configure(app)

        with pytest.raises(WebComPyException, match="already configured"):
            port.configure(app)

    def test_configure_uses_default_base_url(self):
        port = ServerFetchPort()
        assert port._base_url == "/"


class TestServerFetchPortUnconfigured:
    @pytest.mark.asyncio
    async def test_self_site_fetch_before_configure_returns_500(self):
        port = ServerFetchPort()
        response = await port.fetch("/api/data")

        assert response.status_code == 500
        assert response.ok is False
        assert "not configured" in response.text


class TestServerFetchPortSelfSiteRouting:
    @pytest.mark.asyncio
    async def test_blocked_path_returns_500(self):
        async def api_handler(request):
            return JSONResponse({"data": "ok"})

        app = Starlette(routes=[Route("/api/data", endpoint=api_handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=["/"])

        response = await port.fetch("/")

        assert response.status_code == 500
        assert response.ok is False
        assert "blocked" in response.text

    @pytest.mark.asyncio
    async def test_non_blocked_self_site_path_routed_through_asgi(self):
        async def api_handler(request):
            return JSONResponse({"data": "ok"})

        app = Starlette(routes=[Route("/api/data", endpoint=api_handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=["/"])

        response = await port.fetch("/api/data")

        assert response.status_code == 200
        assert response.ok is True
        assert response.json() == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_external_url_uses_external_client(self):
        port = ServerFetchPort()
        app = Starlette(routes=[])
        port.configure(app)

        with pytest.raises(httpx.ConnectError):
            await port.fetch("https://this-domain-does-not-exist.example.com/api/data")

    @pytest.mark.asyncio
    async def test_not_found_self_site_path_returns_404(self):
        app = Starlette(routes=[])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[])

        response = await port.fetch("/nonexistent")

        assert response.status_code == 404


class TestServerFetchPortBlockedPathPatterns:
    @pytest.mark.asyncio
    async def test_dynamic_route_pattern_blocks_concrete_path(self):
        async def user_detail(request):
            return JSONResponse({"user": "data"})

        app = Starlette(routes=[Route("/users/{user_id}", endpoint=user_detail)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=["/users/:id"])

        response = await port.fetch("/users/42")
        assert response.status_code == 500
        assert response.ok is False

    @pytest.mark.asyncio
    async def test_dynamic_route_pattern_does_not_block_different_segment_count(self):
        async def user_detail(request):
            return JSONResponse({"user": "data"})

        app = Starlette(routes=[Route("/users/{user_id}", endpoint=user_detail)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=["/users/:id"])

        response = await port.fetch("/users/42/edit")
        assert response.status_code != 500

    @pytest.mark.asyncio
    async def test_dynamic_route_pattern_does_not_block_unrelated_path(self):
        async def api_handler(request):
            return JSONResponse({"data": "ok"})

        app = Starlette(routes=[Route("/api/data", endpoint=api_handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=["/users/:id"])

        response = await port.fetch("/api/data")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concrete_path_exact_match_is_blocked(self):
        async def user_detail(request):
            return JSONResponse({"user": "data"})

        app = Starlette(routes=[Route("/users/{user_id}", endpoint=user_detail)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=["/users/42"])

        response = await port.fetch("/users/42")
        assert response.status_code == 500

        response = await port.fetch("/users/999")
        assert response.status_code != 500


class TestServerFetchPortBaseUrlResolution:
    @pytest.mark.asyncio
    async def test_self_site_path_resolved_with_base_url(self):
        async def handler(request):
            return JSONResponse({"path": str(request.url.path)})

        app = Starlette(routes=[Route("/myapp/api/data", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[], base_url="/myapp/")

        response = await port.fetch("/api/data")

        assert response.status_code == 200
        assert response.json() == {"path": "/myapp/api/data"}

    @pytest.mark.asyncio
    async def test_self_site_path_with_default_base_url(self):
        async def handler(request):
            return JSONResponse({"path": str(request.url.path)})

        app = Starlette(routes=[Route("/api/data", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[], base_url="/")

        response = await port.fetch("/api/data")

        assert response.status_code == 200
        assert response.json() == {"path": "/api/data"}

    @pytest.mark.asyncio
    async def test_relative_path_resolved_against_base_url(self):
        async def handler(request):
            return JSONResponse({"path": str(request.url.path)})

        app = Starlette(routes=[Route("/myapp/api/data", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[], base_url="/myapp/")

        response = await port.fetch("./api/data")

        assert response.status_code == 200
        assert response.json() == {"path": "/myapp/api/data"}


class TestServerFetchPortClose:
    @pytest.mark.asyncio
    async def test_close_cleans_up_both_clients(self):
        port = ServerFetchPort()
        app = Starlette(routes=[])
        port.configure(app)

        assert port._external_client is not None
        assert port._self_site_client is not None

        await port.close()

        client = httpx.AsyncClient()
        assert not client.is_closed
        await client.aclose()
