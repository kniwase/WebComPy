import pytest

from webcompy.ports._browser._fetch import BrowserFetchPort
from webcompy.ports._fetch import Response
from webcompy_server.ports._fetch import ServerFetchPort
from webcompy_testing import FakeFetchPort, RecordedRequest


def _response() -> Response:
    return Response(text="", headers={}, status_code=200, status_text="OK", ok=True)


class TestFakeFetchPortRecording:
    @pytest.mark.asyncio
    async def test_binary_body_passes_through_unchanged(self):
        port = FakeFetchPort(responses={("POST", "/api"): _response()})
        await port.fetch("/api", method="POST", body=b"\x00\x01\xff")
        assert port.requests[0].body == b"\x00\x01\xff"

    @pytest.mark.asyncio
    async def test_requests_recorded_in_order(self):
        port = FakeFetchPort(responses={("GET", "/a"): _response(), ("POST", "/b"): _response()})
        await port.fetch("/a")
        await port.fetch("/b", method="POST", body="hello", headers={"x": "1"})
        assert [r.url for r in port.requests] == ["/a", "/b"]
        assert isinstance(port.requests[0], RecordedRequest)
        assert port.requests[1].body == "hello"
        assert port.requests[1].headers == {"x": "1"}

    @pytest.mark.asyncio
    async def test_stream_records_request(self):
        port = FakeFetchPort(responses={("GET", "/s"): _response()}, streams={("GET", "/s"): ["chunk"]})
        stream = await port.stream("/s")
        async for _ in stream:
            pass
        assert len(port.requests) == 1
        assert port.requests[0].url == "/s"


class TestCacheKeyDeterminism:
    def test_browser_cache_key_deterministic_for_bytes(self):
        port = object.__new__(BrowserFetchPort)
        body = bytes(range(256))
        first = port._cache_key("/api", "POST", body)
        second = port._cache_key("/api", "POST", bytes(range(256)))
        assert first == second
        assert str(body) not in first

    def test_browser_cache_key_keeps_text_bodies_readable(self):
        port = object.__new__(BrowserFetchPort)
        assert port._cache_key("/api", "POST", "hello") == "POST:/api:hello"

    def test_server_cache_key_deterministic_for_bytes(self):
        port = ServerFetchPort()
        body = b"\xff" * 64
        first = port._cache_key("/api", "POST", body)
        second = port._cache_key("/api", "POST", b"\xff" * 64)
        assert first == second
        assert str(body) not in first
