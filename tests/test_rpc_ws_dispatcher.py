from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient

import webcompy_server.rpc._subscriptions as subs_mod
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_server.rpc._ws_endpoint import create_rpc_ws_endpoint

_RPC_PATH = "/rpc"


def _add(a: int, b: int = 0) -> int:
    return a + b


def _echo(value: str = "") -> str:
    return value


def _boom() -> None:
    raise RuntimeError("boom")


@dataclass
class User:
    id: int
    name: str


def _get_user(user: User) -> User:
    if not isinstance(user, User):
        raise TypeError(f"expected User instance, got {type(user).__name__}")
    return user


def _get_typed() -> dict:
    return {"data": b"hello", "price": Decimal("1.5"), "at": datetime(2024, 1, 2, 3, 4, 5)}


async def _ticker(interval: float = 0.02) -> object:
    import itertools

    for i in itertools.count(1):
        await asyncio.sleep(interval)
        yield {"seq": i}


def _make_registry() -> ProcedureRegistry:
    registry = ProcedureRegistry()
    registry.register("add", _add)
    registry.register("echo", _echo)
    registry.register("boom", _boom)
    registry.register("get_user", _get_user)
    registry.register("get_typed", _get_typed)
    registry.register_subscription("ticker", _ticker, replay_size=256)
    return registry


@pytest.fixture
def app() -> Starlette:
    registry = _make_registry()
    return Starlette(routes=[WebSocketRoute(_RPC_PATH, create_rpc_ws_endpoint(registry))])


class TestWSCalls:
    def test_single_call_round_trip(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "add", "params": {"a": 2, "b": 3}, "id": 1})
            response = ws.receive_json()
            assert response == {"jsonrpc": "2.0", "result": 5, "id": 1}

    def test_positional_params(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "add", "params": [5], "id": "x"})
            assert ws.receive_json()["result"] == 5

    def test_typed_result_meta_matches_http(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "get_typed", "id": 1})
            body = ws.receive_json()
            assert body["result"] == {"data": "aGVsbG8=", "price": "1.5", "at": "2024-01-02T03:04:05"}
            assert body["meta"] == {"/data": "bytes", "/price": "decimal", "/at": "datetime"}

    def test_unknown_method_maps_to_method_not_found(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "missing", "id": 1})
            body = ws.receive_json()
            assert body["error"]["code"] == -32601
            assert body["id"] == 1

    def test_internal_error_hides_details(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "boom", "id": 1})
            body = ws.receive_json()
            assert body["error"]["code"] == -32603
            assert "boom" not in body["error"]["message"]

    def test_invalid_request_validation_matches_http(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "1.0", "method": "add", "params": {"a": 1}, "id": 1})
            assert ws.receive_json()["error"]["code"] == -32600

    def test_parse_error_frame(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_text("{invalid json")
            body = ws.receive_json()
            assert body["error"]["code"] == -32700
            assert body["id"] is None

    def test_batch_round_trip(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            batch = [
                {"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 1},
                {"jsonrpc": "2.0", "method": "add", "params": {"a": 2}, "id": 2},
            ]
            ws.send_text(json.dumps(batch))
            response = ws.receive_json()
            assert isinstance(response, list)
            by_id = {entry["id"]: entry for entry in response}
            assert by_id[1]["result"] == 1
            assert by_id[2]["result"] == 2

    def test_notification_produces_no_frame(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "echo", "params": {"value": "hi"}})
            ws.send_json({"jsonrpc": "2.0", "method": "add", "params": {"a": 9}, "id": 1})
            response = ws.receive_json()
            assert response == {"jsonrpc": "2.0", "result": 9, "id": 1}

    def test_ping_answered_with_pong(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "_webcompy.ping", "params": {}})
            response = ws.receive_json()
            assert response["method"] == "_webcompy.pong"

    def test_close_notification_closes_with_1011(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "_webcompy.close"})
            with pytest.raises(Exception) as exc_info:
                while True:
                    ws.receive_text()
            assert getattr(exc_info.value, "code", None) == 1011


def _receive_events(ws, sub_id: str, count: int) -> list[int]:
    cursors: list[int] = []
    while len(cursors) < count:
        frame = ws.receive_json()
        if frame.get("method") != "_webcompy.event":
            continue
        params = frame["params"]
        if params.get("subscription_id") == sub_id:
            cursors.append(params["cursor"])
    return cursors


class TestSubscriptions:
    def test_subscribe_live_events_monotonic_cursor(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.subscribe",
                    "params": {"method": "ticker", "params": {"interval": 0.01}},
                    "id": 1,
                }
            )
            response = ws.receive_json()
            assert response["result"]["resync_required"] is False
            sub_id = response["result"]["subscription_id"]
            assert sub_id
            cursors = _receive_events(ws, sub_id, 3)
            assert cursors == sorted(cursors)
            assert len(set(cursors)) == len(cursors)

    def test_unsubscribe_stops_delivery(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.subscribe",
                    "params": {"method": "ticker", "params": {"interval": 0.01}},
                    "id": 1,
                }
            )
            sub_id = ws.receive_json()["result"]["subscription_id"]
            _receive_events(ws, sub_id, 1)
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.unsubscribe",
                    "params": {"subscription_id": sub_id},
                }
            )
            # after unsubscribe, a subsequent call's response arrives before any event
            ws.send_json({"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 99})
            frame = ws.receive_json()
            assert frame["id"] == 99
            assert "result" in frame

    def test_connection_close_releases_per_connection_state(self, app: Starlette) -> None:
        with TestClient(app) as client:
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "ticker", "params": {"interval": 0.01}},
                        "id": 1,
                    }
                )
                sub_id = ws.receive_json()["result"]["subscription_id"]
                last_cursor = _receive_events(ws, sub_id, 2)[-1]
            # connection closed; stream survives the grace period -> rejoin replays
            time.sleep(0.1)
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "ticker", "params": {"interval": 0.01}, "last_cursor": last_cursor},
                        "id": 2,
                    }
                )
                response = ws.receive_json()
                assert response["result"]["subscription_id"]
                new_sub = response["result"]["subscription_id"]
                cursors = _receive_events(ws, new_sub, 3)
                assert cursors[0] > last_cursor
                assert cursors == list(range(cursors[0], cursors[0] + len(cursors)))

    def test_rejoin_replays_before_live_exactly_once(self, app: Starlette) -> None:
        with TestClient(app) as client:
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "ticker", "params": {"interval": 0.01}},
                        "id": 1,
                    }
                )
                sub_id = ws.receive_json()["result"]["subscription_id"]
                last_cursor = _receive_events(ws, sub_id, 4)[-1]
            time.sleep(0.15)  # outage: source keeps emitting into the buffer
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "ticker", "params": {"interval": 0.01}, "last_cursor": last_cursor},
                        "id": 2,
                    }
                )
                response = ws.receive_json()
                new_sub = response["result"]["subscription_id"]
                cursors = _receive_events(ws, new_sub, 12)
                assert cursors[0] == last_cursor + 1
                assert cursors == list(range(cursors[0], cursors[0] + len(cursors))), "no gaps, no duplicates"

    def test_cursor_older_than_buffer_floor_resync(self, app: Starlette) -> None:
        with TestClient(app) as client:
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "ticker", "params": {"interval": 0.01}},
                        "id": 1,
                    }
                )
                sub_id = ws.receive_json()["result"]["subscription_id"]
                _receive_events(ws, sub_id, 2)
            # rejoin with a cursor older than the buffer floor -> resync
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "ticker", "params": {"interval": 0.01}, "last_cursor": 0},
                        "id": 2,
                    }
                )
                response = ws.receive_json()
                assert response["result"]["resync_required"] is True
                assert response["result"]["subscription_id"] is None

    def test_subscription_decoded_typed_params(self) -> None:
        registry = ProcedureRegistry()

        def _encode_user(user: User) -> dict[str, Any]:
            return {"id": user.id, "name": user.name}

        def _decode_user(data: dict[str, Any]) -> User:
            return User(data["id"], data["name"])

        registry.register_type_handler(User, _encode_user, _decode_user)

        async def _user_ticker(user: User) -> object:
            yield {"user_id": user.id}

        registry.register_subscription("user_ticker", _user_ticker)
        typed_app = Starlette(routes=[WebSocketRoute(_RPC_PATH, create_rpc_ws_endpoint(registry))])
        with TestClient(typed_app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.subscribe",
                    "params": {
                        "method": "user_ticker",
                        "params": {"user": {"id": 7, "name": "alice"}},
                        "meta": {"/user": f"{User.__module__}.{User.__qualname__}"},
                    },
                    "id": 1,
                }
            )
            response = ws.receive_json()
            assert response["result"]["subscription_id"]
            sub_id = response["result"]["subscription_id"]
            cursors = _receive_events(ws, sub_id, 1)
            assert len(cursors) == 1

    def test_unregistered_subscription_method_not_found(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.subscribe",
                    "params": {"method": "not_a_subscription", "params": {}},
                    "id": 1,
                }
            )
            response = ws.receive_json()
            assert response["error"]["code"] == -32601

    def test_stream_reaped_after_idle_grace(self, app: Starlette, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(subs_mod, "_STREAM_IDLE_TIMEOUT", 0.3)
        with TestClient(app) as client:
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "ticker", "params": {"interval": 0.01}},
                        "id": 1,
                    }
                )
                sub_id = ws.receive_json()["result"]["subscription_id"]
                last_cursor = _receive_events(ws, sub_id, 2)[-1]
            # after the idle grace expires the stream is reaped; a rejoin with the
            # old cursor hits a fresh stream -> resync_required (observable cleanup)
            time.sleep(0.5)
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "ticker", "params": {"interval": 0.01}, "last_cursor": last_cursor},
                        "id": 2,
                    }
                )
                response = ws.receive_json()
                assert response["result"]["resync_required"] is True
