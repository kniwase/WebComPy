from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

import webcompy.realtime._ws as ws_mod
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._keys import WEBSOCKET_PORT_KEY
from webcompy.realtime import ConnectionState
from webcompy.rpc import RpcError, RpcSubscriptionState, RpcWsClient
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_testing import FakeWebSocketPort

WS_URL = "/_webcompy-rpc"


@pytest.fixture
def rt_env(monkeypatch):
    scope = DIScope()
    port = FakeWebSocketPort()
    registry = ProcedureRegistry()
    scope.provide(WEBSOCKET_PORT_KEY, port)
    scope.provide(RPC_REGISTRY_KEY, registry)
    token = _active_di_scope.set(scope)
    monkeypatch.setattr(ws_mod, "_get_app_di_scope", lambda: scope)
    yield SimpleNamespace(scope=scope, port=port, registry=registry)
    _active_di_scope.reset(token)


def _frames(port: FakeWebSocketPort) -> list[dict[str, Any]]:
    return [json.loads(f) for f in port.sent_frames(WS_URL)]


class TestClientCalls:
    @pytest.mark.asyncio
    async def test_call_round_trip_typed(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        task = asyncio.create_task(client.call("add", {"a": 2, "b": 3}, result_type=int))
        await asyncio.sleep(0)
        request = _frames(rt_env.port)[-1]
        assert request["method"] == "add"
        assert request["params"] == {"a": 2, "b": 3}
        req_id = request["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": 5, "id": req_id}))
        assert await task == 5
        client.close()

    @pytest.mark.asyncio
    async def test_error_response_raises_rpc_error(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        task = asyncio.create_task(client.call("missing"))
        await asyncio.sleep(0)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(
            WS_URL,
            json.dumps({"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": req_id}),
        )
        with pytest.raises(RpcError) as exc_info:
            await task
        assert exc_info.value.code == -32601
        client.close()

    @pytest.mark.asyncio
    async def test_call_fails_fast_when_not_open(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        with pytest.raises(RpcError, match="not open"):
            await client.call("add", {"a": 1})
        client.close()

    @pytest.mark.asyncio
    async def test_in_flight_call_fails_on_disconnect(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        task = asyncio.create_task(client.call("add", {"a": 1}, result_type=int))
        await asyncio.sleep(0)
        rt_env.port.emit_close(WS_URL, code=1006, reason="abnormal", was_clean=False)
        with pytest.raises(RpcError, match="connection lost"):
            await task
        assert client.state.value == ConnectionState.RECONNECTING
        client.close()

    @pytest.mark.asyncio
    async def test_calls_work_after_reconnect(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rt_env.port.emit_close(WS_URL, code=1006, reason="abnormal", was_clean=False)
        await asyncio.sleep(0.1)  # retry opens a new socket
        rt_env.port.emit_open(WS_URL)
        assert client.state.value == ConnectionState.OPEN
        task = asyncio.create_task(client.call("add", {"a": 4, "b": 1}, result_type=int))
        await asyncio.sleep(0)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": 5, "id": req_id}))
        assert await task == 5
        client.close()

    @pytest.mark.asyncio
    async def test_notify_fire_and_forget(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        await client.notify("record", {"name": "n1"})
        request = _frames(rt_env.port)[-1]
        assert request["method"] == "record"
        assert "id" not in request
        client.close()


class TestClientSubscriptions:
    @pytest.mark.asyncio
    async def test_subscribe_delivers_ordered_typed_events(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        sub = client.subscribe("ticker", {"interval": 0.1}, event_type=dict)
        await asyncio.sleep(0)
        request = _frames(rt_env.port)[-1]
        assert request["method"] == "_webcompy.subscribe"
        assert request["params"]["method"] == "ticker"
        assert request["params"]["params"] == {"interval": 0.1}
        sub_id = "s1"
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {"jsonrpc": "2.0", "result": {"subscription_id": sub_id, "resync_required": False}, "id": request["id"]}
            ),
        )
        await asyncio.sleep(0)
        assert sub.state.value == RpcSubscriptionState.ACTIVE
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.event",
                    "params": {"subscription_id": sub_id, "cursor": 1, "data": {"seq": 1}},
                }
            ),
        )
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.event",
                    "params": {"subscription_id": sub_id, "cursor": 2, "data": {"seq": 2}},
                }
            ),
        )
        got: list[dict[str, Any]] = []
        async for event in sub:
            got.append(event)
            if len(got) >= 2:
                break
        assert got == [{"seq": 1}, {"seq": 2}]
        assert sub.last_cursor.value == 2
        client.close()

    @pytest.mark.asyncio
    async def test_unsubscribe_finishes_iterator_and_notifies_server(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        sub = client.subscribe("ticker", {}, event_type=dict)
        await asyncio.sleep(0)
        request = _frames(rt_env.port)[-1]
        sub_id = "s1"
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {"jsonrpc": "2.0", "result": {"subscription_id": sub_id, "resync_required": False}, "id": request["id"]}
            ),
        )
        await asyncio.sleep(0)
        sub.close()
        await asyncio.sleep(0)
        unsubs = [f for f in _frames(rt_env.port) if f.get("method") == "_webcompy.unsubscribe"]
        assert unsubs and unsubs[-1]["params"]["subscription_id"] == sub_id
        assert sub.state.value == RpcSubscriptionState.CLOSED
        with pytest.raises(StopAsyncIteration):
            await sub.__anext__()
        client.close()

    @pytest.mark.asyncio
    async def test_rejoin_with_last_cursor_after_reconnect(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        sub = client.subscribe("ticker", {}, event_type=dict)
        await asyncio.sleep(0)
        request = _frames(rt_env.port)[-1]
        sub_id = "s1"
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {"jsonrpc": "2.0", "result": {"subscription_id": sub_id, "resync_required": False}, "id": request["id"]}
            ),
        )
        await asyncio.sleep(0)
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.event",
                    "params": {"subscription_id": sub_id, "cursor": 41, "data": {"seq": 41}},
                }
            ),
        )
        await asyncio.sleep(0)
        assert sub.last_cursor.value == 41
        # disconnect then reconnect -> rejoin sends last_cursor
        rt_env.port.emit_close(WS_URL, code=1006, reason="abnormal", was_clean=False)
        await asyncio.sleep(0.1)
        rt_env.port.emit_open(WS_URL)
        await asyncio.sleep(0)
        sub_requests = [f for f in _frames(rt_env.port) if f.get("method") == "_webcompy.subscribe"]
        assert sub_requests
        assert sub_requests[-1]["params"]["last_cursor"] == 41
        client.close()

    @pytest.mark.asyncio
    async def test_resync_required_surfaces_on_subscription(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        sub = client.subscribe("ticker", {}, event_type=dict)
        await asyncio.sleep(0)
        request = _frames(rt_env.port)[-1]
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {"jsonrpc": "2.0", "result": {"subscription_id": None, "resync_required": True}, "id": request["id"]}
            ),
        )
        await asyncio.sleep(0)
        assert sub.state.value == RpcSubscriptionState.RESYNC_REQUIRED
        with pytest.raises(StopAsyncIteration):
            await sub.__anext__()
        client.close()


class TestHeartbeat:
    @pytest.mark.asyncio
    async def test_timeout_forces_abnormal_close_and_reconnect(self, rt_env) -> None:
        client = RpcWsClient(
            heartbeat_interval=0.05,
            heartbeat_timeout=0.1,
            reconnect_base_delay=0.01,
        )
        rt_env.port.emit_open(WS_URL)
        await asyncio.sleep(0.12)
        pings = [f for f in _frames(rt_env.port) if f.get("method") == "_webcompy.ping"]
        assert pings, "expected heartbeat pings"
        await asyncio.sleep(0.1)
        # no pong arrives -> force_close engages the reconnect loop
        assert client.state.value == ConnectionState.RECONNECTING
        await asyncio.sleep(0.1)
        rt_env.port.emit_open(WS_URL)
        await asyncio.sleep(0.05)
        assert client.state.value == ConnectionState.OPEN
        client.close()

    @pytest.mark.asyncio
    async def test_pong_keeps_connection_alive(self, rt_env) -> None:
        client = RpcWsClient(
            heartbeat_interval=0.05,
            heartbeat_timeout=0.2,
            reconnect_base_delay=0.01,
        )
        rt_env.port.emit_open(WS_URL)

        async def _pong_loop() -> None:
            while True:
                await asyncio.sleep(0.1)
                rt_env.port.emit_message(
                    WS_URL, json.dumps({"jsonrpc": "2.0", "method": "_webcompy.pong", "params": {}})
                )

        pong_task = asyncio.create_task(_pong_loop())
        try:
            await asyncio.sleep(0.4)
            assert client.state.value == ConnectionState.OPEN, "pongs should keep the connection alive"
        finally:
            pong_task.cancel()
        client.close()

    @pytest.mark.asyncio
    async def test_disabled_when_interval_none(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        await asyncio.sleep(0.15)
        pings = [f for f in _frames(rt_env.port) if f.get("method") == "_webcompy.ping"]
        assert pings == []
        assert client.state.value == ConnectionState.OPEN
        client.close()
