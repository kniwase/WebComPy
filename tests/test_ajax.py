from dataclasses import dataclass

import pytest

from webcompy.ajax import HttpClient, TypedResponseError
from webcompy.ajax._fetch import Response, WebComPyHttpClientException
from webcompy.di._scope import DIScope
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy_testing import FakeFetchPort


@dataclass
class User:
    id: int
    name: str


class TestResponse:
    def test_basic_response(self):
        r = Response(text="hello", headers={"content-type": "text/plain"}, status_code=200, reason="OK", ok=True)
        assert r.text == "hello"
        assert r.headers == {"content-type": "text/plain"}
        assert r.status_code == 200
        assert r.ok is True

    def test_error_response(self):
        r = Response(text="not found", headers={}, status_code=404, reason="Not Found", ok=False)
        assert r.ok is False

    def test_json_parsing(self):
        r = Response(
            text='{"key": "value"}', headers={"content-type": "application/json"}, status_code=200, reason="OK", ok=True
        )
        assert r.json() == {"key": "value"}

    def test_raise_for_status_success(self):
        r = Response(text="ok", headers={}, status_code=200, reason="OK", ok=True)
        r.raise_for_status()

    def test_raise_for_status_error(self):
        r = Response(text="error", headers={}, status_code=500, reason="Internal Server Error", ok=False)
        try:
            r.raise_for_status()
            raise AssertionError("Should have raised")
        except WebComPyHttpClientException:
            pass

    def test_repr(self):
        r = Response(text="ok", headers={}, status_code=200, reason="OK", ok=True)
        r = repr(r)
        assert "200" in r


class TestHttpClientTyped:
    def _scope(self, responses):
        scope = DIScope()
        scope.provide(FETCH_PORT_KEY, FakeFetchPort(responses=responses))
        return scope

    @pytest.mark.asyncio
    async def test_untyped_returns_response(self):
        port_response = _port_response('{"id": 1, "name": "ada"}')
        with self._scope({("GET", "/api/users/1"): port_response}):
            result = await HttpClient.get("/api/users/1")
            assert isinstance(result, Response)
            assert result.json() == {"id": 1, "name": "ada"}

    @pytest.mark.asyncio
    async def test_typed_returns_dataclass(self):
        with self._scope({("GET", "/api/users/1"): _port_response('{"id": 1, "name": "ada"}')}):
            result = await HttpClient.get("/api/users/1", response_type=User)
            assert isinstance(result, User)
            assert result.name == "ada"

    @pytest.mark.asyncio
    async def test_typed_list(self):
        with self._scope(
            {("GET", "/api/users"): _port_response('[{"id": 1, "name": "ada"}, {"id": 2, "name": "lin"}]')}
        ):
            result = await HttpClient.get("/api/users", response_type=list[User])
            assert isinstance(result, list)
            assert all(isinstance(u, User) for u in result)
            assert result[0].name == "ada"

    @pytest.mark.asyncio
    async def test_typed_scalar(self):
        with self._scope({("GET", "/api/count"): _port_response("3")}):
            result = await HttpClient.get("/api/count", response_type=int)
            assert result == 3

    @pytest.mark.asyncio
    async def test_non_2xx_raises_before_deserialization(self):
        with (
            self._scope({("GET", "/api/users/1"): _port_response("not json", status_code=404, ok=False)}),
            pytest.raises(WebComPyHttpClientException),
        ):
            await HttpClient.get("/api/users/1", response_type=User)

    @pytest.mark.asyncio
    async def test_invalid_json_raises_typed_response_error(self):
        with (
            self._scope({("GET", "/api/users/1"): _port_response("not json")}),
            pytest.raises(TypedResponseError, match="Failed to parse response as JSON"),
        ):
            await HttpClient.get("/api/users/1", response_type=User)

    @pytest.mark.asyncio
    async def test_schema_mismatch_raises_typed_response_error(self):
        with (
            self._scope({("GET", "/api/users/1"): _port_response('{"id": "x", "name": "ada"}')}),
            pytest.raises(TypedResponseError, match="Response does not match schema"),
        ):
            await HttpClient.get("/api/users/1", response_type=User)

    @pytest.mark.asyncio
    async def test_post_typed(self):
        with self._scope({("POST", "/api/users"): _port_response('{"id": 3, "name": "grace"}')}):
            result = await HttpClient.post("/api/users", json={"name": "grace"}, response_type=User)
            assert isinstance(result, User)
            assert result.id == 3


def _port_response(text, status_code=200, ok=True):
    from webcompy.ports._fetch import Response as PortResponse

    return PortResponse(
        text=text,
        headers={"content-type": "application/json"},
        status_code=status_code,
        status_text="OK" if ok else "Error",
        ok=ok,
    )
