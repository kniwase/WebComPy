from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest

from webcompy.ajax._sse import _format_sse_event
from webcompy.di import DIScope
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.ports._fetch import FetchPort, FetchStream, Response
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.rpc import RpcError, RpcHttpClient, RpcStream, RpcStreamState, StreamingProcedure
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_testing import FakeFetchPort


@dataclass
class Item:
    n: int


@dataclass
class CountParams:
    n: int


async def _count_up(p: CountParams) -> AsyncIterator[int]:
    for i in range(1, p.n + 1):
        yield i


def _sse_text(*events: tuple[str, str]) -> str:
    return "".join(_format_sse_event(event_type, data) for event_type, data in events)


def _item_event(payload: object) -> str:
    return json.dumps({"data": payload, "meta": None})


def _json_error_response() -> Response:
    body = json.dumps({"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1})
    return Response(
        text=body,
        headers={"content-type": "application/json"},
        status_code=200,
        status_text="OK",
        ok=True,
    )


@pytest.fixture
def rpc_env():
    registry = ProcedureRegistry()
    fetch_port = FakeFetchPort()
    scope = DIScope()
    scope.__enter__()
    try:
        scope.provide(FETCH_PORT_KEY, fetch_port)
        scope.provide(RPC_REGISTRY_KEY, registry)
        yield registry, fetch_port
    finally:
        scope.__exit__(None, None, None)


def _client() -> RpcHttpClient:
    return RpcHttpClient()


def _proc() -> StreamingProcedure[CountParams, int]:
    return StreamingProcedure("count_up", CountParams, int)


class TestStreamClient:
    @pytest.mark.asyncio
    async def test_contract_call_returns_sync_stream_handle(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        text = _sse_text(
            ("item", _item_event(1)),
            ("done", "null"),
        )
        fetch_port._streams[("POST", "/_webcompy-rpc")] = [text]
        stream = _proc()(_client(), CountParams(n=1))

        assert isinstance(stream, RpcStream)
        assert not asyncio.iscoroutine(stream)
        assert [item async for item in stream] == [1]

    @pytest.mark.asyncio
    async def test_json_error_fails_stream_before_first_item(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        key = ("POST", "/_webcompy-rpc")
        fetch_port._responses[key] = _json_error_response()

        rpc_stream = _proc()(_client(), CountParams(n=1))
        assert isinstance(rpc_stream, RpcStream)

        with pytest.raises(RpcError) as exc_info:
            async for _item in rpc_stream:
                pass
        assert exc_info.value.code == -32601
        assert rpc_stream.state.value == RpcStreamState.FAILED

    @pytest.mark.asyncio
    async def test_sse_stream_yields_typed_items_across_chunk_boundaries(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        text = _sse_text(
            ("item", _item_event(1)),
            ("item", _item_event(2)),
            ("done", "null"),
        )
        mid = len(text) // 2
        fetch_port._streams[("POST", "/_webcompy-rpc")] = [text[:mid], text[mid:]]

        rpc_stream = _proc()(_client(), CountParams(n=2))
        items = [item async for item in rpc_stream]

        assert items == [1, 2]
        assert rpc_stream.state.value == RpcStreamState.CLOSED

    @pytest.mark.asyncio
    async def test_mid_stream_error_event_raises_rpc_error(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        text = _sse_text(
            ("item", _item_event(1)),
            ("error", json.dumps({"code": -32603, "message": "Internal error", "data": {"x": 1}})),
        )
        fetch_port._streams[("POST", "/_webcompy-rpc")] = [text]

        rpc_stream = _proc()(_client(), CountParams(n=2))
        iterator = rpc_stream.__aiter__()
        assert await iterator.__anext__() == 1
        with pytest.raises(RpcError) as exc_info:
            await iterator.__anext__()
        assert exc_info.value.code == -32603
        assert exc_info.value.data == {"x": 1}
        assert rpc_stream.state.value == RpcStreamState.FAILED

    @pytest.mark.asyncio
    async def test_truncated_stream_without_done_fails(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        text = _sse_text(("item", _item_event(1)))
        fetch_port._streams[("POST", "/_webcompy-rpc")] = [text]

        rpc_stream = _proc()(_client(), CountParams(n=2))
        iterator = rpc_stream.__aiter__()
        assert await iterator.__anext__() == 1
        with pytest.raises(RpcError, match="ended unexpectedly"):
            await iterator.__anext__()

    @pytest.mark.asyncio
    async def test_close_aborts_the_fetch(self) -> None:
        registry = ProcedureRegistry()
        registry.bind(_proc(), _count_up)
        release = asyncio.Event()
        port = _ControlledPort(release)
        scope = DIScope()
        scope.__enter__()
        try:
            scope.provide(FETCH_PORT_KEY, port)
            scope.provide(RPC_REGISTRY_KEY, registry)
            rpc_stream = _proc()(_client(), CountParams(n=1))
            assert isinstance(rpc_stream, RpcStream)
        finally:
            scope.__exit__(None, None, None)

        for _ in range(5):
            await asyncio.sleep(0)
        rpc_stream.close()

        assert port.aborted is True
        assert rpc_stream.state.value == RpcStreamState.CLOSED

    @pytest.mark.asyncio
    async def test_non_json_non_sse_body_fails_the_stream(self, rpc_env) -> None:
        _, fetch_port = rpc_env
        fetch_port._responses[("POST", "/_webcompy-rpc")] = Response(
            text="not json",
            headers={"content-type": "text/plain"},
            status_code=200,
            status_text="OK",
            ok=True,
        )

        rpc_stream = _proc()(_client(), CountParams(n=1))
        with pytest.raises(RpcError, match="Invalid JSON-RPC response"):
            async for _item in rpc_stream:
                pass


class _StaticStream(FetchStream):
    def __init__(self, text: str) -> None:
        super().__init__(200, {"content-type": "text/event-stream"}, True)
        self._text = text
        self._done = False

    async def __anext__(self) -> str:
        if self._done:
            raise StopAsyncIteration
        self._done = True
        return self._text


class _RecordingPort(FetchPort):
    def __init__(self) -> None:
        self.bodies: list[str] = []

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        raise AssertionError("fetch must not be used for streams")

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> FetchStream:
        self.bodies.append(body or "")
        return _StaticStream(_sse_text(("done", "null")))


class _NoopPort:
    noop = True


class _ControlledPort(FetchPort):
    def __init__(self, release: asyncio.Event) -> None:
        self._release = release
        self.aborted = False

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        raise AssertionError("fetch must not be used for streams")

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> FetchStream:
        return _ControlledStream(self)


class _ControlledStream(FetchStream):
    def __init__(self, port: _ControlledPort) -> None:
        super().__init__(200, {"content-type": "text/event-stream"}, True)
        self._port = port
        self._yielded = False

    async def __anext__(self) -> str:
        await self._port._release.wait()
        if self._yielded:
            raise StopAsyncIteration
        self._yielded = True
        return _sse_text(("item", _item_event(1)))

    def close(self) -> None:
        if self._closed:
            return
        super().close()
        self._port.aborted = True


class TestStreamClientEnvelopeAndSsr:
    @pytest.mark.asyncio
    async def test_envelope_carries_stream_flag(self) -> None:
        registry = ProcedureRegistry()
        port = _RecordingPort()
        scope = DIScope()
        scope.__enter__()
        try:
            scope.provide(FETCH_PORT_KEY, port)
            scope.provide(RPC_REGISTRY_KEY, registry)
            rpc_stream = _proc()(_client(), CountParams(n=2))
        finally:
            scope.__exit__(None, None, None)

        for _ in range(20):
            await asyncio.sleep(0)
            if port.bodies:
                break

        envelope = json.loads(port.bodies[0])
        assert envelope["stream"] is True
        assert envelope["method"] == "count_up"
        assert envelope["params"] == {"n": 2}
        assert "id" in envelope
        assert [item async for item in rpc_stream] == []
        assert rpc_stream.state.value == RpcStreamState.CLOSED

    @pytest.mark.asyncio
    async def test_outside_browser_returns_closed_stream_with_warning(self) -> None:
        registry = ProcedureRegistry()
        scope = DIScope()
        scope.__enter__()
        try:
            scope.provide(FETCH_PORT_KEY, _NoopPort())
            scope.provide(RPC_REGISTRY_KEY, registry)
            import warnings

            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                rpc_stream = _proc()(_client(), CountParams(n=1))
        finally:
            scope.__exit__(None, None, None)

        assert isinstance(rpc_stream, RpcStream)
        assert not asyncio.iscoroutine(rpc_stream)
        assert rpc_stream.state.value == RpcStreamState.CLOSED
        assert [item async for item in rpc_stream] == []
