from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Iterator
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


async def _finite(interval: float = 0.01) -> object:
    for i in range(1, 4):
        await asyncio.sleep(interval)
        yield {"seq": i}


async def _six_events() -> object:
    for i in range(1, 7):
        yield {"seq": i}


async def _count_up(n: int) -> AsyncIterator[int]:
    for i in range(1, n + 1):
        yield i


def _count_up_sync(n: int) -> Iterator[int]:
    yield from range(1, n + 1)


async def _fail_midway() -> AsyncIterator[int]:
    yield 1
    raise RuntimeError("boom")


def _hub_of(endpoint) -> subs_mod.SubscriptionHub:
    return next(c.cell_contents for c in endpoint.__closure__ if isinstance(c.cell_contents, subs_mod.SubscriptionHub))


def _make_registry() -> ProcedureRegistry:
    registry = ProcedureRegistry()
    registry.register("add", _add)
    registry.register("echo", _echo)
    registry.register("boom", _boom)
    registry.register("get_user", _get_user)
    registry.register("get_typed", _get_typed)
    registry.register("count_up", _count_up)
    registry.register("count_up_sync", _count_up_sync)
    registry.register("fail_midway", _fail_midway)
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

    def test_cursor_older_than_buffer_floor_resync(self) -> None:
        registry = ProcedureRegistry()
        registry.register_subscription("ticker", _ticker, replay_size=3)
        typed_app = Starlette(routes=[WebSocketRoute(_RPC_PATH, create_rpc_ws_endpoint(registry))])
        with TestClient(typed_app) as client:
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
            # let the tiny buffer evict the client's events: the rejoin cannot
            # fully recover, so it must answer resync_required
            time.sleep(0.3)
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
                assert response["result"]["subscription_id"] is None

    def test_rejoin_with_cursor_zero_replays_full_buffer(self, app: Starlette) -> None:
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
                _receive_events(ws, sub_id, 3)
            time.sleep(0.1)  # outage: the source keeps emitting into the buffer
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "ticker", "params": {"interval": 0.01}, "last_cursor": 0},
                        "id": 2,
                    }
                )
                new_sub = ws.receive_json()["result"]["subscription_id"]
                cursors = _receive_events(ws, new_sub, 5)
                assert cursors[0] == 1, "rejoin with cursor 0 replays from the first buffered event"
                assert cursors == list(range(1, len(cursors) + 1)), "no gaps when replaying from cursor 0"

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

    def test_subscribe_notification_is_ignored(self, app: Starlette) -> None:
        endpoint = app.router.routes[0].endpoint
        hub = _hub_of(endpoint)
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            # a notification-form subscribe (no id) must produce no response and
            # must not create a subscription server-side
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.subscribe",
                    "params": {"method": "ticker", "params": {"interval": 0.01}},
                }
            )
            ws.send_json({"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 99})
            frame = ws.receive_json()
            assert frame["id"] == 99, "the id-less subscribe must not produce a response frame"
            assert "result" in frame
            assert hub._streams == {}, "an id-less subscribe must not create a subscription stream"

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

    def test_resync_on_fresh_stream_reaps_the_orphan(self, app: Starlette) -> None:
        endpoint = app.router.routes[0].endpoint
        hub = _hub_of(endpoint)
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            # the stream does not exist yet (e.g. server restarted while the client
            # was disconnected); the rejoin is answered with resync_required and
            # the freshly created stream must be reaped, not left running forever
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.subscribe",
                    "params": {"method": "ticker", "params": {"interval": 0.01}, "last_cursor": 5},
                    "id": 1,
                }
            )
            response = ws.receive_json()
            assert response["result"]["resync_required"] is True
            assert hub._streams == {}, "the orphaned stream must be reaped"

    def test_finished_source_stream_reaped_and_not_reused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(subs_mod, "_STREAM_IDLE_TIMEOUT", 0.1)
        registry = ProcedureRegistry()
        registry.register_subscription("finite", _finite)
        endpoint = create_rpc_ws_endpoint(registry)
        hub = _hub_of(endpoint)
        app = Starlette(routes=[WebSocketRoute(_RPC_PATH, endpoint)])
        with TestClient(app) as client:
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "finite", "params": {"interval": 0.01}},
                        "id": 1,
                    }
                )
                sub_id = ws.receive_json()["result"]["subscription_id"]
                assert _receive_events(ws, sub_id, 3) == [1, 2, 3]
            # the source exhausted; after the grace period the stream is reaped
            time.sleep(0.4)
            assert hub._streams == {}, "the finished stream must be reaped"
            # a later subscribe must not attach to the dead stream: a fresh stream
            # is created and events flow again
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "_webcompy.subscribe",
                        "params": {"method": "finite", "params": {"interval": 0.01}},
                        "id": 2,
                    }
                )
                new_sub = ws.receive_json()["result"]["subscription_id"]
                assert new_sub != sub_id
                assert _receive_events(ws, new_sub, 1) == [1]

    @pytest.mark.asyncio
    async def test_reap_does_not_evict_a_replacement_stream(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(subs_mod, "_STREAM_IDLE_TIMEOUT", 0.05)
        registry = ProcedureRegistry()
        registry.register_subscription("finite", _finite)
        hub = subs_mod.SubscriptionHub(registry)
        key = ("finite", "null")

        class _FakeConn:
            def __init__(self) -> None:
                self.queue: asyncio.Queue = asyncio.Queue()
                self.subscriptions: dict[str, subs_mod._Stream] = {}

            def send(self, frame: Any) -> None:
                self.queue.put_nowait(frame)

        conn_a = _FakeConn()
        hub.handle_subscribe(
            conn_a,
            {
                "jsonrpc": "2.0",
                "method": "_webcompy.subscribe",
                "params": {"method": "finite", "params": None},
                "id": 1,
            },
        )
        stream_s1 = hub._streams[key]
        for _ in range(200):
            if stream_s1.source_task.done():
                break
            await asyncio.sleep(0.001)
        assert stream_s1.source_task.done()
        # a fresh subscribe replaces the finished stream while the old one is
        # still attached (reap early-returns because S1 has a subscriber)
        conn_b = _FakeConn()
        hub.handle_subscribe(
            conn_b,
            {
                "jsonrpc": "2.0",
                "method": "_webcompy.subscribe",
                "params": {"method": "finite", "params": None},
                "id": 2,
            },
        )
        stream_s2 = hub._streams[key]
        assert stream_s2 is not stream_s1
        # the first subscriber detaches; the old stream's idle timer fires and
        # must not evict the replacement stream's hub entry
        sub_id_a = next(iter(conn_a.subscriptions))
        hub.handle_unsubscribe(
            conn_a,
            {
                "jsonrpc": "2.0",
                "method": "_webcompy.unsubscribe",
                "params": {"subscription_id": sub_id_a},
            },
        )
        await asyncio.sleep(0.15)
        assert hub._streams.get(key) is stream_s2, "reaping the finished stream must not evict its replacement"

    @pytest.mark.asyncio
    async def test_rejoin_full_replay_at_buffer_floor_minus_one(self) -> None:
        registry = ProcedureRegistry()
        registry.register_subscription("six", _six_events, replay_size=3)
        hub = subs_mod.SubscriptionHub(registry)
        info = registry.get_subscription("six")
        assert info is not None
        stream = subs_mod._Stream(hub, info, "null", {})
        stream.start_source()
        for _ in range(200):
            if stream.cursor >= 6:
                break
            await asyncio.sleep(0.001)
        assert stream.cursor == 6
        assert stream.buffer[0][0] == 4  # the buffer holds exactly 4, 5, 6
        # the client's last event was exactly the evicted one: every missed event
        # is still buffered, so a full replay recovers without resync_required
        replay, resync = stream.check_rejoin(3)
        assert resync is False
        assert [c for c, _, _ in replay] == [4, 5, 6]
        assert stream.check_rejoin(2) == ([], True)  # a missed evicted event still resyncs
        assert [c for c, _, _ in stream.check_rejoin(4)[0]] == [5, 6]
        assert stream.check_rejoin(6) == ([], False)  # nothing missed
        assert stream.check_rejoin(7) == ([], True)  # cursor ahead of the stream
        hub.reap(stream)


def _closed_slow_procedure(closed: list[bool]):
    async def _slow() -> AsyncIterator[int]:
        try:
            yield 1
            await asyncio.sleep(3600)
        finally:
            closed.append(True)

    return _slow


def _wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        time.sleep(0.01)
        assert time.monotonic() < deadline, "condition not met within timeout"


class TestStreamCalls:
    def test_flagged_call_acks_with_stream_id(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "count_up", "params": {"n": 2}, "id": 7, "stream": True})
            response = ws.receive_json()
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 7
            assert isinstance(response["result"]["stream_id"], str)

    def test_items_flow_as_event_frames_without_cursor(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "count_up", "params": {"n": 2}, "id": 1, "stream": True})
            ack = ws.receive_json()
            stream_id = ack["result"]["stream_id"]
            data: list[int] = []
            done: dict[str, Any] | None = None
            while len(data) < 2 or done is None:
                frame = ws.receive_json()
                if frame.get("method") == "_webcompy.event":
                    params = frame["params"]
                    assert params.get("stream_id") == stream_id
                    assert "cursor" not in params
                    data.append(params["data"])
                elif frame.get("method") == "_webcompy.stream_done":
                    assert frame["params"]["stream_id"] == stream_id
                    done = frame
            assert data == [1, 2]

    def test_sync_generator_streams_items(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "count_up_sync", "params": {"n": 2}, "id": 1, "stream": True})
            ack = ws.receive_json()
            stream_id = ack["result"]["stream_id"]
            data: list[int] = []
            done: dict[str, Any] | None = None
            while len(data) < 2 or done is None:
                frame = ws.receive_json()
                if frame.get("method") == "_webcompy.event":
                    data.append(frame["params"]["data"])
                elif frame.get("method") == "_webcompy.stream_done":
                    assert frame["params"]["stream_id"] == stream_id
                    done = frame
            assert data == [1, 2]

    def test_mid_stream_exception_emits_error_without_done(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "fail_midway", "id": 1, "stream": True})
            ack = ws.receive_json()
            stream_id = ack["result"]["stream_id"]
            frames = [ws.receive_json(), ws.receive_json()]
            assert [f.get("method") for f in frames] == ["_webcompy.event", "_webcompy.stream_error"]
            error_params = frames[1]["params"]
            assert error_params["stream_id"] == stream_id
            assert error_params["code"] == -32603
            assert "boom" not in error_params["message"]

    def test_stream_cancel_stops_the_generator(self) -> None:
        closed: list[bool] = []
        registry = ProcedureRegistry()
        registry.register("slow", _closed_slow_procedure(closed))
        endpoint = create_rpc_ws_endpoint(registry)
        app = Starlette(routes=[WebSocketRoute(_RPC_PATH, endpoint)])
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "slow", "id": 1, "stream": True})
            stream_id = ws.receive_json()["result"]["stream_id"]
            assert ws.receive_json()["params"]["stream_id"] == stream_id
            ws.send_json({"jsonrpc": "2.0", "method": "_webcompy.stream_cancel", "params": {"stream_id": stream_id}})
            _wait_until(lambda: bool(closed))
            assert closed == [True]

    def test_socket_close_cancels_all_streams(self) -> None:
        closed: list[bool] = []
        registry = ProcedureRegistry()
        registry.register("slow", _closed_slow_procedure(closed))
        endpoint = create_rpc_ws_endpoint(registry)
        app = Starlette(routes=[WebSocketRoute(_RPC_PATH, endpoint)])
        with TestClient(app) as client:
            with client.websocket_connect(_RPC_PATH) as ws:
                ws.send_json({"jsonrpc": "2.0", "method": "slow", "id": 1, "stream": True})
                stream_id = ws.receive_json()["result"]["stream_id"]
                assert ws.receive_json()["params"]["stream_id"] == stream_id
            _wait_until(lambda: bool(closed))
            assert closed == [True]

    def test_streams_are_not_shared_across_calls(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "count_up", "params": {"n": 2}, "id": 1, "stream": True})
            ws.send_json({"jsonrpc": "2.0", "method": "count_up", "params": {"n": 2}, "id": 2, "stream": True})
            stream_ids: set[str] = set()
            while len(stream_ids) < 2:
                frame = ws.receive_json()
                result = frame.get("result")
                if isinstance(result, dict) and "stream_id" in result:
                    stream_ids.add(result["stream_id"])
            assert len(stream_ids) == 2

    def test_stream_mismatch_rules_apply_on_websocket(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "count_up", "params": {"n": 1}, "id": 1})
            assert ws.receive_json()["error"]["code"] == -32600
            ws.send_json({"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 2, "stream": True})
            assert ws.receive_json()["error"]["code"] == -32600
            ws.send_json({"jsonrpc": "2.0", "method": "missing", "id": 3, "stream": True})
            assert ws.receive_json()["error"]["code"] == -32601
            ws.send_json({"jsonrpc": "2.0", "method": "count_up", "params": {"n": "x"}, "id": 4, "stream": True})
            assert ws.receive_json()["error"]["code"] == -32602

    def test_notification_to_streaming_procedure_does_not_execute(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json({"jsonrpc": "2.0", "method": "count_up", "params": {"n": 1}})
            ws.send_json({"jsonrpc": "2.0", "method": "add", "params": {"a": 9}, "id": 99})
            response = ws.receive_json()
            assert response["id"] == 99
            assert "result" in response

    def test_streaming_entry_in_batch_answers_error_per_entry(self, app: Starlette) -> None:
        with TestClient(app) as client, client.websocket_connect(_RPC_PATH) as ws:
            ws.send_json(
                [
                    {"jsonrpc": "2.0", "method": "count_up", "params": {"n": 1}, "id": 1, "stream": True},
                    {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 2},
                ]
            )
            body = ws.receive_json()
            by_id = {entry["id"]: entry for entry in body}
            assert by_id[1]["error"]["code"] == -32600
            assert by_id[2]["result"] == 3
