from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

import webcompy.realtime._ws as ws_mod
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._keys import WEBSOCKET_PORT_KEY
from webcompy.rpc import RpcError, RpcStream, RpcStreamState, RpcWsClient
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_testing import FakeWebSocketPort

WS_URL = "/_webcompy-rpc"


@dataclass
class SsrCountParams:
    n: int


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


class TestClientStreams:
    @pytest.mark.asyncio
    async def test_stream_ack_and_typed_items_then_done(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {"n": 2}, result_type=int)
        request = _frames(rt_env.port)[-1]
        assert request["method"] == "count"
        assert request["stream"] is True
        req_id = request["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id}))
        await asyncio.sleep(0)
        assert rpc_stream.state.value == RpcStreamState.OPEN

        rt_env.port.emit_message(
            WS_URL,
            json.dumps({"jsonrpc": "2.0", "method": "_webcompy.event", "params": {"stream_id": "st1", "data": 1}}),
        )
        rt_env.port.emit_message(
            WS_URL,
            json.dumps({"jsonrpc": "2.0", "method": "_webcompy.event", "params": {"stream_id": "st1", "data": 2}}),
        )
        rt_env.port.emit_message(
            WS_URL,
            json.dumps({"jsonrpc": "2.0", "method": "_webcompy.stream_done", "params": {"stream_id": "st1"}}),
        )
        assert [item async for item in rpc_stream] == [1, 2]
        assert rpc_stream.state.value == RpcStreamState.CLOSED
        client.close()

    @pytest.mark.asyncio
    async def test_items_decoded_with_transfer_meta(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("at", {}, result_type=datetime)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id}))
        await asyncio.sleep(0)
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.event",
                    "params": {"stream_id": "st1", "data": "2024-01-02T03:04:05", "meta": {"": "datetime"}},
                }
            ),
        )
        rt_env.port.emit_message(
            WS_URL,
            json.dumps({"jsonrpc": "2.0", "method": "_webcompy.stream_done", "params": {"stream_id": "st1"}}),
        )
        assert [item async for item in rpc_stream] == [datetime(2024, 1, 2, 3, 4, 5)]
        client.close()

    @pytest.mark.asyncio
    async def test_stream_ack_error_fails_the_stream(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {"jsonrpc": "2.0", "error": {"code": -32600, "message": "not a streaming procedure"}, "id": req_id}
            ),
        )
        await asyncio.sleep(0)
        with pytest.raises(RpcError) as exc_info:
            await rpc_stream.__anext__()
        assert exc_info.value.code == -32600
        assert rpc_stream.state.value == RpcStreamState.FAILED
        client.close()

    @pytest.mark.asyncio
    async def test_stream_error_fails_the_stream(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id}))
        await asyncio.sleep(0)
        rt_env.port.emit_message(
            WS_URL,
            json.dumps({"jsonrpc": "2.0", "method": "_webcompy.event", "params": {"stream_id": "st1", "data": 1}}),
        )
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.stream_error",
                    "params": {"stream_id": "st1", "code": -32603, "message": "Internal error", "data": {"x": 1}},
                }
            ),
        )
        iterator = rpc_stream.__aiter__()
        assert await iterator.__anext__() == 1
        with pytest.raises(RpcError) as exc_info:
            await iterator.__anext__()
        assert exc_info.value.code == -32603
        assert exc_info.value.data == {"x": 1}
        assert rpc_stream.state.value == RpcStreamState.FAILED
        client.close()

    @pytest.mark.asyncio
    async def test_stream_no_drop_when_ack_and_items_pipelined(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {"n": 2}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        frames = [
            {"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id},
            {"jsonrpc": "2.0", "method": "_webcompy.event", "params": {"stream_id": "st1", "data": 1}},
            {"jsonrpc": "2.0", "method": "_webcompy.event", "params": {"stream_id": "st1", "data": 2}},
            {"jsonrpc": "2.0", "method": "_webcompy.stream_done", "params": {"stream_id": "st1"}},
        ]
        for frame in frames:
            rt_env.port.emit_message(WS_URL, json.dumps(frame))
        await asyncio.sleep(0)
        assert [item async for item in rpc_stream] == [1, 2]
        assert rpc_stream.state.value == RpcStreamState.CLOSED
        client.close()

    @pytest.mark.asyncio
    async def test_stream_no_drop_when_ack_and_error_pipelined(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {"n": 2}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        frames = [
            {"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id},
            {"jsonrpc": "2.0", "method": "_webcompy.event", "params": {"stream_id": "st1", "data": 1}},
            {
                "jsonrpc": "2.0",
                "method": "_webcompy.stream_error",
                "params": {"stream_id": "st1", "code": -32603, "message": "boom"},
            },
        ]
        for frame in frames:
            rt_env.port.emit_message(WS_URL, json.dumps(frame))
        await asyncio.sleep(0)
        iterator = rpc_stream.__aiter__()
        assert await iterator.__anext__() == 1
        with pytest.raises(RpcError) as exc_info:
            await iterator.__anext__()
        assert exc_info.value.code == -32603
        assert rpc_stream.state.value == RpcStreamState.FAILED
        client.close()

    @pytest.mark.asyncio
    async def test_close_after_done_does_not_send_cancel(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id}))
        await asyncio.sleep(0)
        rt_env.port.emit_message(
            WS_URL,
            json.dumps({"jsonrpc": "2.0", "method": "_webcompy.stream_done", "params": {"stream_id": "st1"}}),
        )
        await asyncio.sleep(0)
        rpc_stream.close()
        cancels = [f for f in _frames(rt_env.port) if f.get("method") == "_webcompy.stream_cancel"]
        assert cancels == []
        assert rpc_stream.state.value == RpcStreamState.CLOSED
        client.close()

    @pytest.mark.asyncio
    async def test_close_after_error_does_not_send_cancel(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id}))
        await asyncio.sleep(0)
        rt_env.port.emit_message(
            WS_URL,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "_webcompy.stream_error",
                    "params": {"stream_id": "st1", "code": -32603, "message": "boom"},
                }
            ),
        )
        await asyncio.sleep(0)
        rpc_stream.close()
        cancels = [f for f in _frames(rt_env.port) if f.get("method") == "_webcompy.stream_cancel"]
        assert cancels == []
        assert rpc_stream.state.value == RpcStreamState.FAILED
        client.close()

    @pytest.mark.asyncio
    async def test_close_before_ack_sends_cancel_when_ack_arrives(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        rpc_stream.close()
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id}))
        await asyncio.sleep(0)
        cancels = [f for f in _frames(rt_env.port) if f.get("method") == "_webcompy.stream_cancel"]
        assert len(cancels) == 1
        assert cancels[0]["params"] == {"stream_id": "st1"}
        assert rpc_stream.state.value == RpcStreamState.CLOSED
        client.close()

    @pytest.mark.asyncio
    async def test_close_sends_stream_cancel(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id}))
        await asyncio.sleep(0)
        rpc_stream.close()

        cancels = [f for f in _frames(rt_env.port) if f.get("method") == "_webcompy.stream_cancel"]
        assert len(cancels) == 1
        assert cancels[0]["params"] == {"stream_id": "st1"}
        assert rpc_stream.state.value == RpcStreamState.CLOSED
        client.close()

    @pytest.mark.asyncio
    async def test_stream_fails_fast_when_not_open(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        with pytest.raises(RpcError, match="not open"):
            client.stream("count", {})
        client.close()

    @pytest.mark.asyncio
    async def test_stream_fails_fast_when_closed(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        client.close()
        with pytest.raises(RpcError, match="closed"):
            client.stream("count", {})

    @pytest.mark.asyncio
    async def test_disconnect_fails_the_stream(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id}))
        await asyncio.sleep(0)
        rt_env.port.emit_message(
            WS_URL,
            json.dumps({"jsonrpc": "2.0", "method": "_webcompy.event", "params": {"stream_id": "st1", "data": 1}}),
        )
        await asyncio.sleep(0)
        rt_env.port.emit_close(WS_URL, code=1006, reason="abnormal", was_clean=False)
        await asyncio.sleep(0)

        iterator = rpc_stream.__aiter__()
        assert await iterator.__anext__() == 1
        with pytest.raises(RpcError, match="connection lost"):
            await iterator.__anext__()
        assert rpc_stream.state.value == RpcStreamState.FAILED
        client.close()

    @pytest.mark.asyncio
    async def test_disconnected_stream_not_resubscribed_on_reconnect(self, rt_env) -> None:
        client = RpcWsClient(heartbeat_interval=None, reconnect_base_delay=0.01)
        rt_env.port.emit_open(WS_URL)
        rpc_stream = client.stream("count", {}, result_type=int)
        req_id = _frames(rt_env.port)[-1]["id"]
        rt_env.port.emit_message(WS_URL, json.dumps({"jsonrpc": "2.0", "result": {"stream_id": "st1"}, "id": req_id}))
        await asyncio.sleep(0)
        rt_env.port.emit_close(WS_URL, code=1006, reason="abnormal", was_clean=False)
        await asyncio.sleep(0.1)
        rt_env.port.emit_open(WS_URL)
        await asyncio.sleep(0)

        frames = _frames(rt_env.port)
        assert not any(frame.get("method") == "count" and frame.get("stream") is True for frame in frames), (
            "a failed stream must never be re-sent after a reconnect"
        )
        with pytest.raises(RpcError, match="connection lost"):
            await rpc_stream.__anext__()
        client.close()


def test_contract_stream_via_ws_ssr_returns_closed():
    from webcompy.rpc import StreamingProcedure

    async def _count_up(p: SsrCountParams) -> AsyncIterator[int]:
        for i in range(1, p.n + 1):
            yield i

    registry = ProcedureRegistry()
    proc = StreamingProcedure("count_up", SsrCountParams, int)
    registry.bind(proc, _count_up)
    scope = DIScope()
    scope.provide(RPC_REGISTRY_KEY, registry)
    token = _active_di_scope.set(scope)
    try:
        import asyncio
        import warnings

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            client = RpcWsClient()
        s = proc(client, SsrCountParams(n=2))
        assert isinstance(s, RpcStream)

        async def _collect() -> list[int]:
            items: list[int] = []
            async for item in s:
                items.append(item)
            return items

        assert asyncio.run(_collect()) == []
    finally:
        _active_di_scope.reset(token)
