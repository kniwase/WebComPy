import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from webcompy.ajax import HttpClient, TypedResponseError
from webcompy.ajax._fetch import Response, WebComPyHttpClientException
from webcompy.di._scope import DIScope
from webcompy.hydration._transfer_meta import META_BODY_KEY, META_HEADER_NAME
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy_testing import FakeFetchPort


@dataclass
class User:
    id: int
    name: str


@dataclass
class TypedRecord:
    name: str
    blob: bytes
    tags: set[str]
    point: tuple[int, str]
    price: Decimal
    at: datetime
    anything: Any


_RECORD_BODY = (
    '{"name": "alice", "blob": "aW1n", "tags": ["a", "b"], "point": [1, "x"], '
    '"price": "12.34", "at": "2026-01-02T03:04:05", "anything": "aGk="}'
)
_RECORD_META = {
    "/blob": "bytes",
    "/tags": "set",
    "/point": "tuple",
    "/price": "decimal",
    "/at": "datetime",
    "/anything": "bytes",
}


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


class TestHttpClientTransferMeta:
    def _scope(self, responses):
        scope = DIScope()
        scope.provide(FETCH_PORT_KEY, FakeFetchPort(responses=responses))
        return scope

    def _meta_header(self, meta=None):
        return {META_HEADER_NAME.lower(): json.dumps(meta if meta is not None else _RECORD_META)}

    @pytest.mark.asyncio
    async def test_header_mode_restores_types(self):
        response = _port_response(
            _RECORD_BODY,
            headers={**self._meta_header(), "content-type": "application/json"},
        )
        with self._scope({("GET", "/api/record"): response}):
            result = await HttpClient.get("/api/record", response_type=TypedRecord)
        assert result.blob == b"img"
        assert result.tags == {"a", "b"}
        assert result.point == (1, "x")
        assert result.price == Decimal("12.34")
        assert result.at == datetime(2026, 1, 2, 3, 4, 5)
        assert result.anything == b"hi"

    @pytest.mark.asyncio
    async def test_body_mode_restores_types_and_strips_key(self):
        body = json.loads(_RECORD_BODY)
        body[META_BODY_KEY] = _RECORD_META
        response = _port_response(json.dumps(body))
        with self._scope({("GET", "/api/record"): response}):
            result = await HttpClient.get("/api/record", response_type=TypedRecord)
        assert result.blob == b"img"
        assert result.tags == {"a", "b"}
        assert result.price == Decimal("12.34")

    @pytest.mark.asyncio
    async def test_body_key_takes_precedence_over_header(self):
        body = json.loads(_RECORD_BODY)
        body[META_BODY_KEY] = _RECORD_META
        conflicting_header = {META_HEADER_NAME.lower(): json.dumps({"/anything": "set"})}
        response = _port_response(
            json.dumps(body),
            headers={**conflicting_header, "content-type": "application/json"},
        )
        with self._scope({("GET", "/api/record"): response}):
            result = await HttpClient.get("/api/record", response_type=TypedRecord)
        assert result.anything == b"hi"

    @pytest.mark.asyncio
    async def test_absent_metadata_parity(self):
        with (
            self._scope({("GET", "/api/record"): _port_response(_RECORD_BODY)}),
            pytest.raises(TypedResponseError, match="Response does not match schema"),
        ):
            await HttpClient.get("/api/record", response_type=TypedRecord)

    @pytest.mark.asyncio
    async def test_malformed_meta_header_raises(self):
        response = _port_response(
            _RECORD_BODY,
            headers={META_HEADER_NAME.lower(): "{not json", "content-type": "application/json"},
        )
        with (
            self._scope({("GET", "/api/record"): response}),
            pytest.raises(TypedResponseError, match="Malformed"),
        ):
            await HttpClient.get("/api/record", response_type=TypedRecord)

    @pytest.mark.asyncio
    async def test_malformed_meta_body_key_raises(self):
        body = json.loads(_RECORD_BODY)
        body[META_BODY_KEY] = "not_a_dict"
        response = _port_response(json.dumps(body))
        with (
            self._scope({("GET", "/api/record"): response}),
            pytest.raises(TypedResponseError, match="Malformed"),
        ):
            await HttpClient.get("/api/record", response_type=TypedRecord)

    @pytest.mark.asyncio
    async def test_top_level_array_with_header(self):
        body = '["YQ==", "Yg=="]'
        header = {META_HEADER_NAME.lower(): json.dumps({"/0": "bytes", "/1": "bytes"})}
        response = _port_response(
            body,
            headers={**header, "content-type": "application/json"},
        )
        with self._scope({("GET", "/api/blobs"): response}):
            result = await HttpClient.get("/api/blobs", response_type=list[bytes])
        assert result == [b"a", b"b"]

    @pytest.mark.asyncio
    async def test_unknown_tag_lenient_in_http_path(self):
        body = json.loads(_RECORD_BODY)
        body["anything"] = 42
        meta = dict(_RECORD_META)
        meta["/anything"] = "future-type"
        response = _port_response(
            json.dumps(body),
            headers={**self._meta_header(meta), "content-type": "application/json"},
        )
        with self._scope({("GET", "/api/record"): response}):
            result = await HttpClient.get("/api/record", response_type=TypedRecord)
        assert result.anything == 42


def _port_response(text, status_code=200, ok=True, headers=None):
    from webcompy.ports._fetch import Response as PortResponse

    merged = {"content-type": "application/json"}
    if headers:
        merged.update(headers)
    return PortResponse(
        text=text,
        headers=merged,
        status_code=status_code,
        status_text="OK" if ok else "Error",
        ok=ok,
    )
