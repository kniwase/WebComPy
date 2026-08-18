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

    def test_configure_sets_mount_prefixes(self):
        port = ServerFetchPort()
        app = Starlette(routes=[])
        port.configure(app, mount_prefixes=["/api", "/admin/"])

        assert port._mount_prefixes == ["/api", "/admin"]

    def test_configure_defaults_mount_prefixes_to_empty(self):
        port = ServerFetchPort()
        app = Starlette(routes=[])
        port.configure(app)

        assert port._mount_prefixes == []

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

    @pytest.mark.asyncio
    async def test_mount_path_exempt_from_base_url_prefix(self):
        async def handler(request):
            return JSONResponse({"path": str(request.url.path)})

        app = Starlette(routes=[Route("/api/users", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[], base_url="/myapp/", mount_prefixes=["/api"])

        response = await port.fetch("/api/users")

        assert response.status_code == 200
        assert response.json() == {"path": "/api/users"}

    @pytest.mark.asyncio
    async def test_non_mount_path_resolved_with_base_url_alongside_mounts(self):
        async def handler(request):
            return JSONResponse({"path": str(request.url.path)})

        app = Starlette(routes=[Route("/myapp/other/data", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[], base_url="/myapp/", mount_prefixes=["/api"])

        response = await port.fetch("/other/data")

        assert response.status_code == 200
        assert response.json() == {"path": "/myapp/other/data"}

    @pytest.mark.asyncio
    async def test_mount_path_not_blocked_despite_similar_shape(self):
        async def handler(request):
            return JSONResponse({"user": "data"})

        app = Starlette(routes=[Route("/users/42", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=["/users/:id"], mount_prefixes=["/users"])

        response = await port.fetch("/users/42")

        assert response.status_code == 200
        assert response.json() == {"user": "data"}

    @pytest.mark.asyncio
    async def test_mount_root_with_query_params_exempt_from_base_url_prefix(self):
        async def handler(request):
            return JSONResponse({"path": str(request.url.path), "query": str(request.url.query)})

        app = Starlette(routes=[Route("/api", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[], base_url="/myapp/", mount_prefixes=["/api"])

        response = await port.fetch("/api?foo=bar")

        assert response.status_code == 200
        assert response.json() == {"path": "/api", "query": "foo=bar"}

    @pytest.mark.asyncio
    async def test_mount_subpath_with_query_params_exempt_from_base_url_prefix(self):
        async def handler(request):
            return JSONResponse({"path": str(request.url.path), "query": str(request.url.query)})

        app = Starlette(routes=[Route("/api/users", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[], base_url="/myapp/", mount_prefixes=["/api"])

        response = await port.fetch("/api/users?page=2")

        assert response.status_code == 200
        assert response.json() == {"path": "/api/users", "query": "page=2"}

    @pytest.mark.asyncio
    async def test_mount_path_with_fragment_exempt_from_base_url_prefix(self):
        async def handler(request):
            return JSONResponse({"path": str(request.url.path)})

        app = Starlette(routes=[Route("/api/users", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[], base_url="/myapp/", mount_prefixes=["/api"])

        response = await port.fetch("/api/users#section")

        assert response.status_code == 200
        assert response.json() == {"path": "/api/users"}


class TestServerFetchPortClose:
    @pytest.mark.asyncio
    async def test_close_cleans_up_both_clients(self, monkeypatch):
        class _FakeClient:
            def __init__(self):
                self.closed = False

            async def request(self, method, url, *, headers=None, content=None):
                return httpx.Response(200, json={})

            async def aclose(self) -> None:
                self.closed = True

        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: _FakeClient())

        port = ServerFetchPort()
        app = Starlette(routes=[])
        port.configure(app)
        await port.fetch("https://api.example.com/data")

        assert port._external_client is not None
        assert port._self_site_client is not None

        await port.close()

        assert port._external_client.closed is True
        assert port._self_site_client.closed is True


class TestServerFetchPortLazyExternalClient:
    @pytest.mark.asyncio
    async def test_no_client_allocated_before_external_fetch(self):
        port = ServerFetchPort()
        assert port._external_client is None

    @pytest.mark.asyncio
    async def test_external_fetch_creates_client_lazily(self, monkeypatch):
        class _FakeClient:
            def __init__(self):
                self.requested_urls: list[str] = []

            async def request(self, method, url, *, headers=None, content=None):
                self.requested_urls.append(url)
                return httpx.Response(200, json={"ok": True})

            async def aclose(self) -> None:
                pass

        fake = _FakeClient()
        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: fake)

        port = ServerFetchPort()
        assert port._external_client is None

        response = await port.fetch("https://api.example.com/data")

        assert response.ok is True
        assert port._external_client is fake
        assert fake.requested_urls == ["https://api.example.com/data"]

    @pytest.mark.asyncio
    async def test_close_without_external_client_does_not_raise(self):
        port = ServerFetchPort()
        await port.close()

    @pytest.mark.asyncio
    async def test_clone_propagates_unallocated_client(self):
        port = ServerFetchPort()
        clone = port._clone_for_context()
        assert clone._external_client is None

    @pytest.mark.asyncio
    async def test_clone_shares_lazily_created_client(self, monkeypatch):
        class _FakeClient:
            def __init__(self):
                self.closed = False

            async def request(self, method, url, *, headers=None, content=None):
                return httpx.Response(200, json={})

            async def aclose(self) -> None:
                self.closed = True

        fake = _FakeClient()
        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: fake)

        port = ServerFetchPort()
        await port.fetch("https://api.example.com/data")
        clone = port._clone_for_context()

        assert clone._external_client is fake

    @pytest.mark.asyncio
    async def test_unconfigured_render_context_allocates_no_external_client(self, monkeypatch):
        from webcompy.app import WebComPyApp, WebComPyAppConfig
        from webcompy.ports._keys import FETCH_PORT_KEY
        from webcompy_server import configure_server_context

        creations: list[str] = []
        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: creations.append("client") or object())

        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)

        ctx = app.create_render_context("/")
        try:
            port = ctx.di_scope.inject(FETCH_PORT_KEY)
            assert port._external_client is None
        finally:
            ctx.dispose()

        assert creations == [], "no httpx client may be allocated for an unconfigured render context"

    @pytest.mark.asyncio
    async def test_clone_external_fetch_shares_prototype_client(self, monkeypatch):
        class _FakeClient:
            def __init__(self):
                self.requested_urls: list[str] = []

            async def request(self, method, url, *, headers=None, content=None):
                self.requested_urls.append(url)
                return httpx.Response(200, json={"ok": True})

            async def aclose(self) -> None:
                pass

        creations: list[str] = []
        fake = _FakeClient()
        monkeypatch.setattr(
            "httpx.AsyncClient",
            lambda *args, **kwargs: creations.append("client") or fake,
        )

        prototype = ServerFetchPort()
        clone = prototype._clone_for_context()

        response = await clone.fetch("https://api.example.com/data")

        assert response.ok is True
        assert prototype._external_client is fake, "the client must be created on the prototype so all clones share it"
        assert clone._external_client is None
        assert creations == ["client"]
        assert fake.requested_urls == ["https://api.example.com/data"]

    @pytest.mark.asyncio
    async def test_two_clones_share_single_external_client(self, monkeypatch):
        class _FakeClient:
            async def request(self, method, url, *, headers=None, content=None):
                return httpx.Response(200, json={"ok": True})

            async def aclose(self) -> None:
                pass

        creations: list[str] = []
        fake = _FakeClient()
        monkeypatch.setattr(
            "httpx.AsyncClient",
            lambda *args, **kwargs: creations.append("client") or fake,
        )

        prototype = ServerFetchPort()
        clone1 = prototype._clone_for_context()
        clone2 = prototype._clone_for_context()

        await clone1.fetch("https://api.example.com/one")
        await clone2.fetch("https://api.example.com/two")

        assert creations == ["client"], "a single external client must be shared across clones"
        assert prototype._external_client is fake
        assert clone1._prototype is prototype
        assert clone2._prototype is prototype
