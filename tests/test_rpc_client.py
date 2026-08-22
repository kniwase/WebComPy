from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from webcompy.di import DIScope, provide
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.ports._fetch import Response
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.rpc import Procedure, RpcHttpClient, batch, notify
from webcompy.rpc._errors import RpcError
from webcompy.rpc._registry import ProcedureRegistry


async def _run_rpc(c):
    return await c


class _FakeFetchPort:
    def __init__(
        self,
        responses: list[Response] | None = None,
        *,
        responder: Any = None,
    ) -> None:
        self._responses = list(responses or [])
        self._responder = responder
        self.calls: list[tuple[str, str, dict[str, str] | None, str | None]] = []

    def add_response(self, response: Response) -> None:
        self._responses.append(response)

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        self.calls.append((url, method, headers, body))
        if self._responder is not None:
            return self._responder(url, method, headers, body)
        if not self._responses:
            raise AssertionError("No response queued")
        return self._responses.pop(0)


def _json_response(payload: Any, status_code: int = 200) -> Response:
    import json

    text = json.dumps(payload)
    return Response(
        text=text,
        headers={"content-type": "application/json"},
        status_code=status_code,
        status_text="OK",
        ok=status_code < 400,
    )


def _empty_response(status_code: int = 204) -> Response:
    return Response(
        text="",
        headers={},
        status_code=status_code,
        status_text="No Content" if status_code == 204 else "Error",
        ok=status_code < 400,
    )


@dataclass
class User:
    id: int
    name: str


@dataclass
class GetUserParams:
    id: int


@dataclass
class AddParams:
    a: int
    b: int = 0


@dataclass
class PayloadParams:
    dummy: int = 0


@dataclass
class SetItemParams:
    at: datetime


@dataclass
class PointParams:
    point: Any


class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


def _encode_point(point: Point) -> dict[str, int]:
    return {"x": point.x, "y": point.y}


def _decode_point(data: dict[str, int]) -> Point:
    return Point(data["x"], data["y"])


@pytest.fixture
def rpc_env():
    registry = ProcedureRegistry()
    fetch_port = _FakeFetchPort()
    scope = DIScope()
    scope.__enter__()
    try:
        provide(FETCH_PORT_KEY, fetch_port)
        provide(RPC_REGISTRY_KEY, registry)
        client = RpcHttpClient()
        yield registry, fetch_port, client
    finally:
        scope.__exit__(None, None, None)


class TestCall:
    def test_envelope_structure(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": None, "id": 1}))

        import asyncio
        import json

        proc = Procedure("no_such_method", AddParams, type(None))
        asyncio.run(_run_rpc(proc(client, AddParams(a=1))))

        url, method, headers, body = fetch_port.calls[0]
        assert url == "/_webcompy-rpc"
        assert method == "POST"
        assert headers == {"Content-Type": "application/json"}
        envelope = json.loads(body)
        assert envelope["jsonrpc"] == "2.0"
        assert envelope["method"] == "no_such_method"
        assert isinstance(envelope["id"], int)

    def test_successful_call(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": 3, "id": 1}))

        import asyncio

        proc = Procedure("add", AddParams, int)
        result = asyncio.run(_run_rpc(proc(client, AddParams(a=1, b=2))))

        assert result == 3
        url, method, _headers, body = fetch_port.calls[0]
        assert url == "/_webcompy-rpc"
        assert method == "POST"
        import json

        envelope = json.loads(body)
        assert envelope["jsonrpc"] == "2.0"
        assert envelope["method"] == "add"
        assert envelope["params"] == {"a": 1, "b": 2}
        assert isinstance(envelope["id"], int)

    def test_ids_increment(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": 1, "id": 1}))
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": 2, "id": 2}))

        import asyncio
        import json

        proc_a = Procedure("a", AddParams, int)
        proc_b = Procedure("b", AddParams, int)
        asyncio.run(_run_rpc(proc_a(client, AddParams(a=1))))
        asyncio.run(_run_rpc(proc_b(client, AddParams(a=1))))

        first_id = json.loads(fetch_port.calls[0][3])["id"]
        second_id = json.loads(fetch_port.calls[1][3])["id"]
        assert second_id > first_id

    def test_result_type_restores_dataclass(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": {"id": 1, "name": "alice"}, "id": 1}))

        import asyncio

        proc = Procedure("get_user", GetUserParams, User)
        result = asyncio.run(_run_rpc(proc(client, GetUserParams(id=1))))

        assert isinstance(result, User)
        assert result.id == 1
        assert result.name == "alice"

    def test_result_meta_restores_types(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(
            _json_response(
                {
                    "jsonrpc": "2.0",
                    "result": {"data": "aGVsbG8=", "price": "1.5"},
                    "meta": {"/data": "bytes", "/price": "decimal"},
                    "id": 1,
                }
            )
        )

        import asyncio
        from dataclasses import dataclass

        @dataclass
        class Payload:
            data: bytes
            price: Decimal

        proc = Procedure("get_payload", PayloadParams, Payload)
        result = asyncio.run(_run_rpc(proc(client, PayloadParams())))

        assert result == Payload(data=b"hello", price=Decimal("1.5"))

    def test_params_encoded_with_meta(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": None, "id": 1}))

        import asyncio
        import json

        proc = Procedure("set_item", SetItemParams, type(None))
        asyncio.run(_run_rpc(proc(client, SetItemParams(at=datetime(2024, 1, 2, 3, 4, 5)))))

        envelope = json.loads(fetch_port.calls[0][3])
        assert envelope["params"] == {"at": "2024-01-02T03:04:05"}
        assert envelope["meta"] == {"/at": "datetime"}

    def test_custom_type_param_encoded_via_registered_handler(self, rpc_env) -> None:
        registry, fetch_port, client = rpc_env
        registry.register_type_handler(Point, _encode_point, _decode_point)
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": None, "id": 1}))

        import asyncio
        import json

        tag = f"{Point.__module__}.{Point.__qualname__}"

        @dataclass
        class ReflectParams:
            point: Point

        proc = Procedure("reflect", ReflectParams, type(None))
        asyncio.run(_run_rpc(proc(client, ReflectParams(point=Point(3, 4)))))

        envelope = json.loads(fetch_port.calls[0][3])
        assert envelope["params"] == {"point": {"x": 3, "y": 4}}
        assert envelope["meta"] == {"/point": tag}

    def test_error_response_raises_rpc_error(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(
            _json_response(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": "Method not found", "data": {"x": 1}},
                    "id": 1,
                }
            )
        )

        import asyncio

        proc = Procedure("missing", AddParams, int)
        with pytest.raises(RpcError) as exc:
            asyncio.run(_run_rpc(proc(client, AddParams(a=1))))
        assert exc.value.code == -32601
        assert exc.value.message == "Method not found"
        assert exc.value.data == {"x": 1}

    def test_malformed_response_raises(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(_json_response({"result": 1}))

        import asyncio

        proc = Procedure("add", AddParams, int)
        with pytest.raises(RpcError, match="Malformed"):
            asyncio.run(_run_rpc(proc(client, AddParams(a=1))))


class TestNotify:
    def test_notify_sends_envelope_without_id(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(_empty_response())

        import asyncio
        import json

        proc = Procedure("log", AddParams, int)
        c = proc(client, AddParams(a=1))
        result = asyncio.run(notify(c))

        assert result is None
        envelope = json.loads(fetch_port.calls[0][3])
        # notify sends array of id-less envelopes
        assert isinstance(envelope, list)
        assert envelope[0]["jsonrpc"] == "2.0"
        assert envelope[0]["method"] == "log"
        assert "id" not in envelope[0]


class TestBatch:
    def test_batch_returns_results_in_order(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env

        import asyncio
        import json

        def _respond(url, method, headers, body):
            payload = json.loads(body)
            responses = [{"jsonrpc": "2.0", "result": i, "id": entry["id"]} for i, entry in enumerate(payload)]
            return _json_response(responses)

        fetch_port._responder = _respond

        add = Procedure("add", AddParams, int)
        c1 = add(client, AddParams(a=1))
        c2 = add(client, AddParams(a=2))
        results = asyncio.run(batch(c1, c2))

        assert results == (0, 1)

    def test_batch_error_raises_rpc_error(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env

        import asyncio
        import json

        def _respond(url, method, headers, body):
            payload = json.loads(body)
            responses = [
                {"jsonrpc": "2.0", "result": 1, "id": payload[0]["id"]},
                {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": payload[1]["id"]},
            ]
            return _json_response(responses)

        fetch_port._responder = _respond

        add = Procedure("add", AddParams, int)
        missing = Procedure("missing", AddParams, int)
        with pytest.raises(RpcError) as exc:
            asyncio.run(batch(add(client, AddParams(a=1)), missing(client, AddParams(a=1))))
        assert exc.value.code == -32601

    def test_batch_empty_no_io(self, rpc_env) -> None:
        import asyncio

        assert asyncio.run(batch()) == ()

    def test_batch_return_exceptions(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env

        import asyncio
        import json

        def _respond(url, method, headers, body):
            payload = json.loads(body)
            responses = [
                {"jsonrpc": "2.0", "result": 1, "id": payload[0]["id"]},
                {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": payload[1]["id"]},
            ]
            return _json_response(responses)

        fetch_port._responder = _respond

        add = Procedure("add", AddParams, int)
        missing = Procedure("missing", AddParams, int)
        results = asyncio.run(
            batch(add(client, AddParams(a=1)), missing(client, AddParams(a=1)), return_exceptions=True)
        )
        assert results[0] == 1
        assert isinstance(results[1], RpcError)


class TestClientErrors:
    def test_empty_response_raises(self, rpc_env) -> None:
        _, fetch_port, client = rpc_env
        fetch_port.add_response(_empty_response())

        import asyncio

        proc = Procedure("add", AddParams, int)
        with pytest.raises(RpcError, match="Empty response"):
            asyncio.run(_run_rpc(proc(client, AddParams(a=1))))
