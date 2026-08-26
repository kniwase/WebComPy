from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from webcompy.ajax._sse import _format_sse_event
from webcompy.di import DIScope
from webcompy.di._keys import RPC_MIDDLEWARE_KEY, RPC_REGISTRY_KEY
from webcompy.ports._fetch import FetchPort, FetchStream, Response, _BufferedFetchStream
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.rpc import Procedure, RpcCall, RpcError, RpcHttpClient, StreamingProcedure, batch, notify
from webcompy.rpc._errors import INTERNAL_ERROR
from webcompy.rpc._middleware import RpcContext, RpcMiddlewareRegistry, add_rpc_middleware
from webcompy.rpc._registry import ProcedureRegistry


@dataclass
class AddParams:
    a: int
    b: int


@dataclass
class EmptyParams:
    pass


@dataclass
class CountParams:
    n: int


def _response(body: str, status_code: int = 200) -> Response:
    return Response(
        text=body,
        headers={"content-type": "application/json"},
        status_code=status_code,
        status_text="OK",
        ok=status_code < 400,
    )


def _sse_text(*events: tuple[str, str]) -> str:
    return "".join(_format_sse_event(event_type, data) for event_type, data in events)


def _item_event(payload: object) -> str:
    return json.dumps({"data": payload, "meta": None})


class _RecordingFetchPort(FetchPort):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    def _compute(self, envelope: dict[str, Any]) -> Any:
        name = envelope.get("method")
        params = envelope.get("params") or {}
        if name == "add":
            return params.get("a", 0) + params.get("b", 0)
        if name == "echo":
            return params
        return None

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        self.calls.append({"url": url, "method": method, "headers": headers, "body": body})
        request = json.loads(body) if body else {}
        if isinstance(request, list):
            payload = [
                {"jsonrpc": "2.0", "result": self._compute(envelope), "id": envelope.get("id")} for envelope in request
            ]
        else:
            payload = {"jsonrpc": "2.0", "result": self._compute(request), "id": request.get("id")}
        return _response(json.dumps(payload))

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> FetchStream:
        self.stream_calls.append({"headers": headers, "body": body})
        n = 0
        try:
            request_body = json.loads(body or "{}")
            n = (request_body.get("params") or {}).get("n", 0)
        except ValueError:
            n = 0
        events = "".join(_sse_text(("item", _item_event(i))) for i in range(1, n + 1))
        return _BufferedFetchStream(
            200, {"content-type": "text/event-stream"}, True, events + _sse_text(("done", "null"))
        )


@pytest.fixture
def env():
    registry = ProcedureRegistry()
    fetch_port = _RecordingFetchPort()
    middlewares = RpcMiddlewareRegistry()
    scope = DIScope()
    scope.__enter__()
    try:
        scope.provide(FETCH_PORT_KEY, fetch_port)
        scope.provide(RPC_REGISTRY_KEY, registry)
        scope.provide(RPC_MIDDLEWARE_KEY, middlewares)
        yield type("Env", (), {"registry": registry, "fetch": fetch_port, "middlewares": middlewares})
    finally:
        scope.__exit__(None, None, None)


ADD = Procedure("add", AddParams, int)
MOCK = Procedure("mock", EmptyParams, int)


def _client() -> RpcHttpClient:
    return RpcHttpClient()


@pytest.mark.asyncio
async def test_typed_params_visible_in_context(env) -> None:
    seen: list[tuple[str, str]] = []

    async def spy(ctx: RpcContext, next):  # type: ignore[name-defined]
        seen.append((type(ctx.params).__name__, ctx.method))
        return await next(ctx)

    env.middlewares.use(spy)

    assert await ADD(_client(), AddParams(a=1, b=2)) == 3
    assert seen == [("AddParams", "add")]


@pytest.mark.asyncio
async def test_headers_merged_and_content_type_forced(env) -> None:
    async def auth(ctx: RpcContext, next):  # type: ignore[name-defined]
        ctx.headers["Authorization"] = "Bearer token"
        ctx.headers["Content-Type"] = "text/plain"
        return await next(ctx)

    env.middlewares.use(auth)
    await ADD(_client(), AddParams(a=1, b=2))

    sent = env.fetch.calls[-1]["headers"]
    assert sent["Authorization"] == "Bearer token"
    assert sent["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_lowercase_content_type_variant_is_dropped(env) -> None:
    async def auth(ctx: RpcContext, next):  # type: ignore[name-defined]
        ctx.headers["content-type"] = "text/plain"
        return await next(ctx)

    env.middlewares.use(auth)
    await ADD(_client(), AddParams(a=1, b=2))

    sent = env.fetch.calls[-1]["headers"]
    content_types = [k for k in sent if k.lower() == "content-type"]
    assert content_types == ["Content-Type"]
    assert sent["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_params_substitution_reaches_envelope(env) -> None:
    async def bump(ctx: RpcContext, next):  # type: ignore[name-defined]
        if isinstance(ctx.params, AddParams):
            ctx.params = AddParams(a=ctx.params.a + 10, b=ctx.params.b)
        return await next(ctx)

    env.middlewares.use(bump)

    assert await ADD(_client(), AddParams(a=1, b=2)) == 13


@pytest.mark.asyncio
async def test_selective_scoping_by_method(env) -> None:
    async def intercept_mock_only(ctx: RpcContext, next):  # type: ignore[name-defined]
        if ctx.method == "mock":
            return await next(ctx, response={"result": 42})
        return await next(ctx)

    env.middlewares.use(intercept_mock_only)

    assert await MOCK(_client(), EmptyParams()) == 42
    assert len(env.fetch.calls) == 0

    assert await ADD(_client(), AddParams(a=2, b=3)) == 5
    assert len(env.fetch.calls) == 1


@pytest.mark.asyncio
async def test_short_circuit_result_is_validated(env) -> None:
    async def good_mock(ctx: RpcContext, next):  # type: ignore[name-defined]
        return await next(ctx, response={"result": 0})

    env.middlewares.use(good_mock)

    assert await MOCK(_client(), EmptyParams()) == 0
    assert len(env.fetch.calls) == 0


@pytest.mark.asyncio
async def test_short_circuit_validation_failure_raises_rpc_error(env) -> None:
    async def bad_mock(ctx: RpcContext, next):  # type: ignore[name-defined]
        return await next(ctx, response={"result": "not-an-int"})

    env.middlewares.use(bad_mock)

    with pytest.raises(RpcError) as exc_info:
        await MOCK(_client(), EmptyParams())
    assert exc_info.value.code == INTERNAL_ERROR


@pytest.mark.asyncio
async def test_bare_return_without_next_raises(env) -> None:
    async def bare_return(ctx: RpcContext, next):  # type: ignore[name-defined]
        return {"result": 42}

    env.middlewares.use(bare_return)

    with pytest.raises(RuntimeError, match="without calling next"):
        await MOCK(_client(), EmptyParams())
    assert len(env.fetch.calls) == 0


@pytest.mark.asyncio
async def test_notify_receives_middleware_headers(env) -> None:
    PING = Procedure("add", AddParams, int)

    async def auth(ctx: RpcContext, next):  # type: ignore[name-defined]
        ctx.headers["X-Trace"] = "trace-1"
        return await next(ctx)

    env.middlewares.use(auth)

    await notify(PING(_client(), AddParams(a=1, b=1)))

    sent = env.fetch.calls[-1]
    assert sent["headers"]["X-Trace"] == "trace-1"
    assert '"id"' not in (sent["body"] or "")


@pytest.mark.asyncio
async def test_batch_single_chain_execution_with_metadata(env) -> None:
    contexts: list[RpcContext] = []

    async def spy(ctx: RpcContext, next):  # type: ignore[name-defined]
        contexts.append(ctx)
        ctx.headers["X-Batch"] = "1"
        return await next(ctx)

    env.middlewares.use(spy)
    client = _client()

    results = await batch(
        ADD(client, AddParams(a=1, b=2)),
        ADD(client, AddParams(a=2, b=5)),
    )

    assert results == (3, 7)
    assert len(contexts) == 1
    assert contexts[0].is_batch is True
    assert contexts[0].batch_entries is not None
    assert len(contexts[0].batch_entries) == 2
    assert env.fetch.calls[-1]["headers"]["X-Batch"] == "1"


@pytest.mark.asyncio
async def test_batch_synthesis_positional_fragments(env) -> None:
    async def mock_batch(ctx: RpcContext, next):  # type: ignore[name-defined]
        return await next(ctx, response=[{"result": 100}, {"result": 200}])

    env.middlewares.use(mock_batch)
    client = _client()

    results = await batch(
        ADD(client, AddParams(a=1, b=2)),
        ADD(client, AddParams(a=2, b=5)),
    )

    assert results == (100, 200)
    assert env.fetch.calls == []


@pytest.mark.asyncio
async def test_stream_middleware_headers_and_substitution(env) -> None:
    COUNT = StreamingProcedure("count", CountParams, int)

    async def mutate_and_substitute(ctx: RpcContext, next):  # type: ignore[name-defined]
        ctx.headers["X-Stream"] = "1"
        sse = _sse_text(("item", _item_event(10)), ("item", _item_event(20)), ("done", "null"))
        return await next(ctx, stream=_BufferedFetchStream(200, {"content-type": "text/event-stream"}, True, sse))

    env.middlewares.use(mutate_and_substitute)
    stream = COUNT(_client(), CountParams(n=3))

    items = [item async for item in stream]

    assert items == [10, 20]


@pytest.mark.asyncio
async def test_stream_middleware_header_reaches_fetch_stream(env) -> None:
    COUNT = StreamingProcedure("count", CountParams, int)

    async def add_header(ctx: RpcContext, next):  # type: ignore[name-defined]
        ctx.headers["X-Stream"] = "yes"
        return await next(ctx)

    env.middlewares.use(add_header)
    stream = COUNT(_client(), CountParams(n=1))

    items = [item async for item in stream]

    assert items == [1]
    sent = env.fetch.stream_calls[-1]["headers"]
    assert sent["X-Stream"] == "yes"
    assert sent["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_missing_middleware_key_still_works() -> None:
    registry = ProcedureRegistry()
    fetch_port = _RecordingFetchPort()
    scope = DIScope()
    scope.__enter__()
    try:
        scope.provide(FETCH_PORT_KEY, fetch_port)
        scope.provide(RPC_REGISTRY_KEY, registry)

        assert await ADD(_client(), AddParams(a=4, b=6)) == 10
    finally:
        scope.__exit__(None, None, None)


def test_add_rpc_middleware_registers_in_active_scope() -> None:
    middlewares = RpcMiddlewareRegistry()
    scope = DIScope()
    scope.__enter__()
    try:
        scope.provide(RPC_MIDDLEWARE_KEY, middlewares)

        async def mw(ctx: RpcContext, next):  # type: ignore[name-defined]
            return await next(ctx)

        add_rpc_middleware(mw)
        assert middlewares.middlewares == (mw,)
    finally:
        scope.__exit__(None, None, None)


def test_add_rpc_middleware_without_scope_raises() -> None:
    async def mw(ctx: RpcContext, next):  # type: ignore[name-defined]
        return await next(ctx)

    with pytest.raises(RuntimeError, match="No active RPC middleware registry"):
        add_rpc_middleware(mw)


@pytest.mark.asyncio
async def test_notify_fast_path_omits_params_member_when_none(env) -> None:
    call = RpcCall("ping", None, None, _client())

    await notify(call)

    sent = json.loads(env.fetch.calls[-1]["body"])
    assert isinstance(sent, list)
    assert "params" not in sent[0]


@pytest.mark.asyncio
async def test_batch_omits_params_member_when_none(env) -> None:
    transport = _client()

    await batch(ADD(transport, AddParams(a=1, b=2)), RpcCall("ping", None, None, transport))

    sent = json.loads(env.fetch.calls[-1]["body"])
    assert isinstance(sent, list)
    assert "params" not in sent[1]
    assert sent[0]["params"] == {"a": 1, "b": 2}
