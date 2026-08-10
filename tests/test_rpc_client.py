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
from webcompy.rpc import batch, call, notify
from webcompy.rpc._errors import RpcError
from webcompy.rpc._registry import ProcedureRegistry


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
        yield registry, fetch_port
    finally:
        scope.__exit__(None, None, None)


class TestCall:
    def test_envelope_structure(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": None, "id": 1}))

        import asyncio
        import json

        asyncio.run(call("no_such_method"))

        url, method, headers, body = fetch_port.calls[0]
        assert url == "/_webcompy-rpc"
        assert method == "POST"
        assert headers == {"Content-Type": "application/json"}
        envelope = json.loads(body)
        assert envelope["jsonrpc"] == "2.0"
        assert envelope["method"] == "no_such_method"
        assert "params" not in envelope
        assert isinstance(envelope["id"], int)

    def test_successful_call(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": 3, "id": 1}))

        import asyncio

        result = asyncio.run(call("add", {"a": 1, "b": 2}))

        assert result == 3
        url, method, headers, body = fetch_port.calls[0]
        assert url == "/_webcompy-rpc"
        assert method == "POST"
        assert headers == {"Content-Type": "application/json"}
        import json

        envelope = json.loads(body)
        assert envelope["jsonrpc"] == "2.0"
        assert envelope["method"] == "add"
        assert envelope["params"] == {"a": 1, "b": 2}
        assert isinstance(envelope["id"], int)

    def test_ids_increment(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": 1, "id": 1}))
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": 2, "id": 2}))

        import asyncio
        import json

        asyncio.run(call("a"))
        asyncio.run(call("b"))

        first_id = json.loads(fetch_port.calls[0][3])["id"]
        second_id = json.loads(fetch_port.calls[1][3])["id"]
        assert second_id > first_id

    def test_result_type_restores_dataclass(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": {"id": 1, "name": "alice"}, "id": 1}))

        import asyncio

        result = asyncio.run(call("get_user", {"id": 1}, result_type=User))

        assert isinstance(result, User)
        assert result.id == 1
        assert result.name == "alice"

    def test_result_meta_restores_types(self, rpc_env) -> None:
        _, fetch_port = rpc_env
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

        result = asyncio.run(call("get_payload"))

        assert result == {"data": b"hello", "price": Decimal("1.5")}

    def test_params_encoded_with_meta(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": None, "id": 1}))

        import asyncio
        import json

        asyncio.run(call("set_item", {"at": datetime(2024, 1, 2, 3, 4, 5)}))

        envelope = json.loads(fetch_port.calls[0][3])
        assert envelope["params"] == {"at": "2024-01-02T03:04:05"}
        assert envelope["meta"] == {"/at": "datetime"}

    def test_custom_type_param_encoded_via_registered_handler(self, rpc_env) -> None:
        registry, fetch_port = rpc_env
        registry.register_type_handler(Point, _encode_point, _decode_point)
        fetch_port.add_response(_json_response({"jsonrpc": "2.0", "result": None, "id": 1}))

        import asyncio
        import json

        tag = f"{Point.__module__}.{Point.__qualname__}"
        asyncio.run(call("reflect", {"point": Point(3, 4)}))

        envelope = json.loads(fetch_port.calls[0][3])
        assert envelope["params"] == {"point": {"x": 3, "y": 4}}
        assert envelope["meta"] == {"/point": tag}

    def test_error_response_raises_rpc_error(self, rpc_env) -> None:
        _, fetch_port = rpc_env
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

        with pytest.raises(RpcError) as exc:
            asyncio.run(call("missing"))
        assert exc.value.code == -32601
        assert exc.value.message == "Method not found"
        assert exc.value.data == {"x": 1}

    def test_malformed_response_raises(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        fetch_port.add_response(_json_response({"result": 1}))

        import asyncio

        with pytest.raises(RpcError, match="Malformed"):
            asyncio.run(call("add"))


class TestNotify:
    def test_notify_sends_envelope_without_id(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        fetch_port.add_response(_empty_response())

        import asyncio
        import json

        result = asyncio.run(notify("log", {"msg": "hi"}))

        assert result is None
        envelope = json.loads(fetch_port.calls[0][3])
        assert envelope["jsonrpc"] == "2.0"
        assert envelope["method"] == "log"
        assert "id" not in envelope
        assert envelope["params"] == {"msg": "hi"}


class TestBatch:
    def test_batch_returns_results_in_order(self, rpc_env) -> None:
        _, fetch_port = rpc_env

        import asyncio
        import json

        def _respond(url, method, headers, body):
            payload = json.loads(body)
            responses = [{"jsonrpc": "2.0", "result": i, "id": entry["id"]} for i, entry in enumerate(payload)]
            return _json_response(responses)

        fetch_port._responder = _respond

        results = asyncio.run(batch([("add", {"a": 1}), ("add", {"a": 2})]))

        assert results == [0, 1]

    def test_batch_error_raises_rpc_error(self, rpc_env) -> None:
        _, fetch_port = rpc_env

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

        with pytest.raises(RpcError) as exc:
            asyncio.run(batch([("add", {"a": 1}), ("missing", None)]))
        assert exc.value.code == -32601


class TestClientErrors:
    def test_empty_response_raises(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        fetch_port.add_response(_empty_response())

        import asyncio

        with pytest.raises(RpcError, match="Empty response"):
            asyncio.run(call("add"))
