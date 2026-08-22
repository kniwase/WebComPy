from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime

import pytest

from webcompy.components._hooks import _active_component_context
from webcompy.components._libs import Context
from webcompy.rpc import RpcError, RpcStream, RpcStreamState, StreamingProcedure
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.rpc._stream import _decode_stream_item


@dataclass
class Item:
    n: int


@dataclass
class CountParams:
    n: int


async def _count_up(p: CountParams) -> AsyncIterator[int]:
    for i in range(1, p.n + 1):
        yield i


def _typed_stream() -> RpcStream[Item]:
    registry = ProcedureRegistry()
    return RpcStream(decode=lambda data, meta: _decode_stream_item(data, meta, Item, registry))


def test_streaming_bind_and_info():
    registry = ProcedureRegistry()
    proc = StreamingProcedure("count_up", CountParams, int)
    registry.bind(proc, _count_up)
    info = registry.get("count_up")
    assert info is not None
    assert info.is_streaming is True
    assert info.result_schema is int


class TestRpcStream:
    @pytest.mark.asyncio
    async def test_typed_items_decoded_per_item(self) -> None:
        stream = _typed_stream()
        stream._deliver_raw({"n": 1}, None)
        stream._deliver_raw({"n": 2}, None)
        stream._finish()

        assert [item async for item in stream] == [Item(1), Item(2)]
        assert stream.state.value == RpcStreamState.CLOSED

    @pytest.mark.asyncio
    async def test_transfer_meta_applied_before_decode(self) -> None:
        registry = ProcedureRegistry()
        stream = RpcStream(decode=lambda data, meta: _decode_stream_item(data, meta, datetime, registry))
        stream._deliver_raw("2024-01-02T03:04:05", {"": "datetime"})
        stream._finish()

        assert [item async for item in stream] == [datetime(2024, 1, 2, 3, 4, 5)]

    @pytest.mark.asyncio
    async def test_exhaustion_finishes_with_closed_state(self) -> None:
        stream = RpcStream()
        stream._deliver(1)
        stream._deliver(2)
        stream._finish()

        assert [item async for item in stream] == [1, 2]
        assert stream.state.value == RpcStreamState.CLOSED

    @pytest.mark.asyncio
    async def test_mid_stream_error_raises_rpc_error_and_fails_state(self) -> None:
        stream = RpcStream()
        stream._deliver(1)
        stream._fail(RpcError(-32603, "boom", {"detail": "x"}))

        iterator = stream.__aiter__()
        assert await iterator.__anext__() == 1
        with pytest.raises(RpcError) as exc_info:
            await iterator.__anext__()
        assert exc_info.value.code == -32603
        assert exc_info.value.message == "boom"
        assert exc_info.value.data == {"detail": "x"}
        assert stream.state.value == RpcStreamState.FAILED

    @pytest.mark.asyncio
    async def test_queued_items_yielded_before_error_surfaces(self) -> None:
        stream = RpcStream()
        stream._deliver(1)
        stream._deliver(2)
        stream._fail(RpcError(-32603, "boom"))

        iterator = stream.__aiter__()
        assert await iterator.__anext__() == 1
        assert await iterator.__anext__() == 2
        with pytest.raises(RpcError):
            await iterator.__anext__()

    @pytest.mark.asyncio
    async def test_decode_failure_fails_the_stream(self) -> None:
        stream = _typed_stream()
        stream._deliver_raw({"n": 1}, None)
        stream._deliver_raw({"n": "not-an-int"}, None)

        iterator = stream.__aiter__()
        assert await iterator.__anext__() == Item(1)
        with pytest.raises(RpcError):
            await iterator.__anext__()
        assert stream.state.value == RpcStreamState.FAILED

    @pytest.mark.asyncio
    async def test_close_is_idempotent_and_stops_delivery(self) -> None:
        calls: list[str] = []
        stream = RpcStream(cancel=lambda: calls.append("cancel"))
        stream._deliver(1)
        stream.close()
        stream.close()

        assert calls == ["cancel"]
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()
        assert stream.state.value == RpcStreamState.CLOSED

    @pytest.mark.asyncio
    async def test_delivery_after_finish_is_ignored(self) -> None:
        stream = RpcStream()
        stream._finish()
        stream._deliver(99)

        assert [item async for item in stream] == []

    @pytest.mark.asyncio
    async def test_async_with_closes_on_exit(self) -> None:
        calls: list[str] = []
        stream = RpcStream(cancel=lambda: calls.append("cancel"))

        async with stream:
            pass

        assert calls == ["cancel"]
        assert stream.state.value == RpcStreamState.CLOSED

    @pytest.mark.asyncio
    async def test_async_with_closes_on_break(self) -> None:
        calls: list[str] = []
        stream = RpcStream(cancel=lambda: calls.append("cancel"))
        stream._deliver(1)
        stream._deliver(2)

        collected: list[int] = []
        async with stream as active:
            async for item in active:
                collected.append(item)
                if item == 1:
                    break

        assert collected == [1]
        assert calls == ["cancel"]
        assert stream.state.value == RpcStreamState.CLOSED


class TestRpcStreamClosed:
    def test_closed_stream_is_immediately_empty(self) -> None:
        stream = RpcStream(closed=True)

        assert stream.state.value == RpcStreamState.CLOSED
        assert asyncio.run(_collect(stream)) == []

    def test_component_destroy_closes_the_stream(self) -> None:
        ctx = Context(
            props=None,
            slots={},
            component_name="StreamComp",
            title_getter=lambda: "",
            meta_getter=lambda: {},
            title_setter=lambda x: None,
            meta_setter=lambda k, v: None,
        )
        token = _active_component_context.set(ctx)
        try:
            stream = RpcStream()
        finally:
            _active_component_context.reset(token)

        hooks = ctx.__get_lifecyclehooks__()
        assert "on_before_destroy" in hooks
        hooks["on_before_destroy"]()

        assert stream.state.value == RpcStreamState.CLOSED
        assert asyncio.run(_collect(stream)) == []


async def _collect(stream: RpcStream[object]) -> list[object]:
    return [item async for item in stream]
