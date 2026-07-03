from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from webcompy_server.ports._fetch import ServerFetchPort


class TestServerFetchCache:
    @pytest.mark.asyncio
    async def test_cache_population_on_self_site_get(self):
        async def handler(request):
            return JSONResponse({"data": "cached"})

        app = Starlette(routes=[Route("/api/data", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[])

        response1 = await port.fetch("/api/data")
        assert response1.status_code == 200

        assert "/api/data" in port._response_cache
        cached = port._response_cache["/api/data"]
        assert cached.status_code == 200
        assert cached.json() == {"data": "cached"}

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_response(self):
        call_count = 0

        async def handler(request):
            nonlocal call_count
            call_count += 1
            return JSONResponse({"call": call_count})

        app = Starlette(routes=[Route("/api/data", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[])

        response1 = await port.fetch("/api/data")
        assert response1.json() == {"call": 1}
        assert call_count == 1

        response2 = await port.fetch("/api/data")
        assert response2.json() == {"call": 1}
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_miss_makes_network_request(self):
        call_count = 0

        async def handler1(request):
            nonlocal call_count
            call_count += 1
            return JSONResponse({"data": "first"})

        async def handler2(request):
            nonlocal call_count
            call_count += 1
            return JSONResponse({"data": "second"})

        app = Starlette(
            routes=[
                Route("/api/data", endpoint=handler1),
                Route("/api/other", endpoint=handler2),
            ]
        )
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[])

        await port.fetch("/api/data")
        assert call_count == 1
        assert "/api/data" in port._response_cache

        await port.fetch("/api/other")
        assert call_count == 2
        assert "/api/other" in port._response_cache
        assert port._response_cache["/api/other"].json() == {"data": "second"}

    @pytest.mark.asyncio
    async def test_non_get_cache_key_includes_method_and_body(self):
        posted_data = None

        async def post_handler(request):
            nonlocal posted_data
            posted_data = await request.json()
            return JSONResponse({"received": posted_data})

        app = Starlette(routes=[Route("/api/data", endpoint=post_handler, methods=["POST"])])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[])

        await port.fetch("/api/data", method="POST", body='{"key": "value1"}')
        post_cache_key = 'POST:/api/data:{"key": "value1"}'
        assert post_cache_key in port._response_cache

    @pytest.mark.asyncio
    async def test_get_transfer_data_returns_correct_format(self):
        async def handler(request):
            return JSONResponse({"data": "ok"})

        app = Starlette(routes=[Route("/api/data", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[])

        await port.fetch("/api/data")

        transfer_data = port.get_transfer_data()
        assert "/api/data" in transfer_data
        entry = transfer_data["/api/data"]
        assert entry.status_code == 200
        assert isinstance(entry.headers, dict)
        assert entry.body is not None

    @pytest.mark.asyncio
    async def test_clear_cache_empties_the_cache(self):
        async def handler(request):
            return JSONResponse({"data": "ok"})

        app = Starlette(routes=[Route("/api/data", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[])

        await port.fetch("/api/data")
        assert len(port._response_cache) > 0

        port.clear_cache()
        assert len(port._response_cache) == 0

    @pytest.mark.asyncio
    async def test_external_urls_not_cached(self):
        async def handler(request):
            return JSONResponse({"data": "ok"})

        app = Starlette(routes=[Route("/api/data", endpoint=handler)])
        port = ServerFetchPort()
        port.configure(app, blocked_paths=[])

        await port.fetch("/api/data")
        assert len(port._response_cache) == 1
        assert "/api/data" in port._response_cache

        assert port.is_self_site_url("https://example.com/api") is False

    @pytest.mark.asyncio
    async def test_get_transfer_data_excludes_external(self):
        port = ServerFetchPort()
        app = Starlette(routes=[])
        port.configure(app)

        port._response_cache["https://external.com/api"] = type(
            "Resp", (), {"status_code": 200, "headers": {}, "text": "ext"}
        )()
        port._response_cache["/self/api"] = type("Resp", (), {"status_code": 200, "headers": {}, "text": "self"})()

        data = port.get_transfer_data()
        assert "/self/api" in data
        assert "https://external.com/api" in data
