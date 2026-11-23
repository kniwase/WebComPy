---
title: RPC Streaming
description: Stream finite, call-scoped typed responses from server generators with StreamingProcedure and RpcStream over HTTP SSE or WebSocket, including lifecycle states, cancellation, and SSR fallback.
---

# RPC Streaming

`StreamingProcedure` and `RpcStream[T]` model **finite, call-scoped typed streams** — operations such as LLM token generation, multi-step export progress, or chunked file analysis where one request triggers a bounded sequence of typed items until the server generator returns or raises. The exact same contract works over both HTTP (`RpcHttpClient`, via `text/event-stream`) and WebSocket (`RpcWsClient`, multiplexed via `stream_id`).

## When to use

- **Need a bounded stream tied to one RPC request** — use `StreamingProcedure` + `RpcStream`.
- **Need a long-lived broadcast subscription with automatic reconnect and cursor replay** — use `Subscription` + [RPC over WebSocket](/documents/advanced/rpc-websocket).
- **Returning a single value from a request** — use `Procedure` in [RPC Contracts](/documents/advanced/rpc-contracts).
- **Consuming a standalone non-RPC SSE endpoint** — use [Server-Sent Events](/documents/advanced/event-source).

## Setup

Declare a `StreamingProcedure(name, params_type, result_type)` contract in a shared module, bind a sync or async generator on the server via `@app.rpc.bind`, and iterate the returned `RpcStream[T]` on the client:

```python
# my_app/contracts.py — shared by server and client
from dataclasses import dataclass

from webcompy.rpc import StreamingProcedure


@dataclass
class PromptParams:
    prompt: str


@dataclass
class TokenChunk:
    text: str
    done: bool = False


stream_tokens = StreamingProcedure("ai.stream_tokens", PromptParams, TokenChunk)
```

Bind an `async def` generator (or sync generator) returning `AsyncIterator[TokenChunk]` or `Iterator[TokenChunk]` on the server. When served via `webcompy start`, both HTTP SSE (`create_dispatcher_app`) and WebSocket (`create_rpc_ws_endpoint`) mount automatically at `app.rpc.path`:

```python
# my_app/server.py — server generator + optional Starlette host mount
import asyncio
from collections.abc import AsyncIterator

from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute

from webcompy import WebComPyApp
from webcompy_server.rpc import create_dispatcher_app, create_rpc_ws_endpoint
from my_app.contracts import PromptParams, TokenChunk, stream_tokens


def register_streaming(app: WebComPyApp) -> None:
    @app.rpc.bind(stream_tokens)
    async def handle_tokens(params: PromptParams) -> AsyncIterator[TokenChunk]:
        words = params.prompt.split() or ["ready"]
        for word in words:
            await asyncio.sleep(0.05)
            yield TokenChunk(text=f"{word} ")
        yield TokenChunk(text="", done=True)


# Custom Starlette host only:
# host = Starlette(
#     routes=[
#         Route(app.rpc.path, create_dispatcher_app(app.rpc)),
#         WebSocketRoute(app.rpc.path, create_rpc_ws_endpoint(app.rpc)),
#     ]
# )
```

Invoke `stream_tokens(client, params)` on the client with `RpcHttpClient` and iterate asynchronously:

```python
# my_app/components/streamer.py — browser component
from webcompy import use_computed, use_state
from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.elements import html
from webcompy.rpc import RpcError, RpcHttpClient, RpcStreamState
from my_app.contracts import PromptParams, stream_tokens

client = RpcHttpClient()


@define_component()
def TokenViewer(context: ComponentContext[None]):
    output = use_state(lambda: "")
    stream = stream_tokens(client, PromptParams(prompt="Hello from WebComPy streaming"))

    @on_mounted
    async def consume():
        try:
            async for chunk in stream:
                output.value += chunk.text
        except RpcError as err:
            output.value += f"\n[Error {err.code}: {err.message}]"

    return html.DIV(
        {},
        html.P({}, use_computed(lambda: f"Stream state: {stream.state.value.value}")),
        html.PRE({}, output),
    )
```

## Recipes

### Bridge stream chunks and lifecycle state with `to_reactive_list`

Because `RpcStream[T]` implements `AsyncIterator[T]`, `to_reactive_list()` accumulates chunks cleanly while `stream.state` tracks `RpcStreamState` (`OPEN`, `CLOSED`, `FAILED`):

```python
# Server registration
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from webcompy.rpc import StreamingProcedure


@dataclass
class ExportParams:
    report_id: str


@dataclass
class ExportStep:
    percent: int
    message: str


export_report = StreamingProcedure("reports.export", ExportParams, ExportStep)


@app.rpc.bind(export_report)
async def handle_export(params: ExportParams) -> AsyncIterator[ExportStep]:
    for pct, label in [(25, "Querying rows"), (75, "Formatting CSV"), (100, "Complete")]:
        await asyncio.sleep(0.05)
        yield ExportStep(percent=pct, message=label)
```

```python
# Client component
from webcompy import use_computed
from webcompy.aio import to_reactive_list
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.rpc import RpcHttpClient, RpcStreamState

client = RpcHttpClient()


@define_component()
def ExportProgress(context: ComponentContext[None]):
    stream = export_report(client, ExportParams(report_id="q4-sales"))
    steps = to_reactive_list(stream)

    return html.DIV(
        {},
        html.P(
            {},
            use_computed(
                lambda: "Done" if stream.state.value == RpcStreamState.CLOSED else "Running..."
            ),
        ),
        html.UL({}, repeat(steps.items, lambda s: html.LI({}, f"{s.percent}% — {s.message}"))),
    )
```

### Cancel a stream early and clean up server resources

Call `stream.close()` or wrap the stream in `async with ...:` to stop consuming early. Closing cancels the underlying HTTP streaming request (or sends `_webcompy.stream_cancel` on WebSocket) so the server generator exits through its `finally:` block:

```python
# Server generator with resource cleanup
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from webcompy.rpc import StreamingProcedure


@dataclass
class TailParams:
    job_id: str


@dataclass
class LogLine:
    line: str


tail_logs = StreamingProcedure("jobs.tail", TailParams, LogLine)


@app.rpc.bind(tail_logs)
async def handle_tail(params: TailParams) -> AsyncIterator[LogLine]:
    try:
        for i in range(100):
            await asyncio.sleep(0.1)
            yield LogLine(line=f"[{params.job_id}] line {i}")
    finally:
        # Runs when client disconnects or calls stream.close()
        print("Cleaned up log reader for", params.job_id)
```

```python
# Client stopping early with `async with` or `.close()`
from webcompy.rpc import RpcHttpClient

client = RpcHttpClient()

async def read_first_five(job_id: str) -> list[str]:
    collected: list[str] = []
    async with tail_logs(client, TailParams(job_id=job_id)) as stream:
        async for entry in stream:
            collected.append(entry.line)
            if len(collected) >= 5:
                break
    return collected
```

Calling `.close()` manually outside `async with` is idempotent and moves `stream.state.value` to `RpcStreamState.CLOSED`.

### Switch transport to `RpcWsClient` with zero contract changes

Pass an already-open `RpcWsClient` instead of `RpcHttpClient` to multiplex concurrent streams over WebSocket alongside subscriptions and calls:

```python
# Server uses the exact same `@app.rpc.bind(export_report)` above.
# Custom Starlette hosts simply mount `WebSocketRoute(app.rpc.path, create_rpc_ws_endpoint(app.rpc))`.
from webcompy import ConnectionState
from webcompy.rpc import RpcWsClient


async def run_over_ws(ws_client: RpcWsClient) -> list[ExportStep]:
    # Require OPEN state before calling .stream() on RpcWsClient
    assert ws_client.state.value == ConnectionState.OPEN
    stream = export_report(ws_client, ExportParams(report_id="q4-sales"))
    return [step async for step in stream]
```

### Mock or inspect HTTP streams in `RpcMiddleware`

Intercept HTTP `StreamingProcedure` calls targeting your bound server handler (such as `@app.rpc.bind(export_report)` shown above) inside component setup with `add_rpc_middleware` and supply a synthetic SSE `FetchStream` via `await next(ctx, stream=...)` (covered further alongside full middleware composition in upcoming middleware docs):

```python
# Server target (shared contract + server registration; short-circuited in offline preview)
@app.rpc.bind(export_report)
async def handle_export_live(params: ExportParams) -> AsyncIterator[ExportStep]:
    yield ExportStep(percent=100, message=f"Exported {params.report_id}")
```

```python
# Client component installing a mock stream for offline demos / tests
import json
from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.elements import html
from webcompy.ports import FetchStream
from webcompy.rpc import RpcContext, RpcHttpClient, add_rpc_middleware
from webcompy.signal import use_state


class _MockSSEStream(FetchStream):
    def __init__(self, body: str) -> None:
        super().__init__(200, {"content-type": "text/event-stream"}, True)
        self._body = body
        self._sent = False

    async def __anext__(self) -> str:
        if self._closed or self._sent:
            raise StopAsyncIteration
        self._sent = True
        return self._body


@define_component()
def OfflineStreamPreview(context: ComponentContext[None]):
    preview = use_state(lambda: "")
    client = RpcHttpClient()

    async def mock_export(ctx: RpcContext, next):
        if ctx.method == "reports.export":
            sse = (
                f'event: item\ndata: {json.dumps({"data": {"percent": 100, "message": "Mocked"}})}\n\n'
                'event: done\ndata: null\n\n'
            )
            return await next(ctx, stream=_MockSSEStream(sse))
        return await next(ctx)

    add_rpc_middleware(mock_export)
    stream = export_report(client, ExportParams(report_id="demo"))

    @on_mounted
    async def load():
        async for step in stream:
            preview.value = f"{step.percent}% {step.message}"

    return html.P({}, preview)
```

## Behavior notes

- **Stream lifecycle states (`RpcStreamState`)**:
  - `OPEN` — active and buffering incoming items into an `asyncio.Queue`.
  - `CLOSED` — server finished cleanly, or `.close()` / `async with` closed the stream.
  - `FAILED` — server emitted an error frame, an item failed typed decoding, or the transport failed; awaiting the next iteration step raises the `RpcError`.
- **Typed item codec & allowlist**: Each streamed item carries `data` and optional `meta` encoded identically to ordinary `Procedure` results and decoded via the same strict type allowlist (`app.rpc.register_type_handler(...)`).
- **Component lifecycle cleanup**: Creating an `RpcStream` inside component setup automatically chains `stream.close()` onto `on_before_destroy`, cancelling in-flight HTTP or WebSocket streams when the component unmounts.
- **Wire transport details**:
  - Over HTTP (`RpcHttpClient`), issuing `"stream": true` against `create_dispatcher_app(app.rpc)` returns `Content-Type: text/event-stream` carrying `event: item`, `event: done`, and `event: error` frames.
  - Over WebSocket (`RpcWsClient`), the initial request returns `{"stream_id": "..."}`, followed by `_webcompy.event` items, `_webcompy.stream_done`, `_webcompy.stream_error`, and client-sent `_webcompy.stream_cancel`.
- **SSR and hydration**: During server rendering and `webcompy generate`, `StreamingProcedure` calls on both `RpcHttpClient` and `RpcWsClient` emit a `UserWarning` and return an immediately exhausted `RpcStream` with `state.value == RpcStreamState.CLOSED`. Stream results are never baked into `<script id="__webcompy_data__">`.

## Pitfalls

- **Using `StreamingProcedure` for infinite pub/sub feeds**: `RpcStream` is call-scoped and never reconnects or replays missed events if the connection drops. Use `Subscription` and `RpcWsClient` from [RPC over WebSocket](/documents/advanced/rpc-websocket) for long-lived feeds.
- **Omitting the element type on the server generator return annotation**: `@app.rpc.bind(streaming_contract)` requires a parameterized generator return annotation (`AsyncIterator[TokenChunk]`, `Iterator[TokenChunk]`, or two/three-arg generator forms) matching `contract.result_type`; bare `AsyncIterator` or `Any` fails binding validation at startup.
- **Leaving `RpcError` uncaught during `async for`**: An exception inside the server generator or an unexpected stream drop transitions `stream.state` to `FAILED` and raises `RpcError` directly from `async for ... in stream:`. Wrap iteration in `try ... except RpcError:` whenever UI code drives recovery.
- **Forgetting to close streams started outside a component**: Service functions running outside component setup must either use `async with contract(client, params) as stream:` or call `stream.close()` explicitly when stopping early.

## Next steps

- Handle persistent subscriptions with cursor replay in [RPC over WebSocket](/documents/advanced/rpc-websocket).
- Review `Procedure`, `batch()`, `notify()`, and the transport routing guide in [RPC Contracts](/documents/advanced/rpc-contracts).
- Inspect HTTP dispatcher configuration and `RpcError` codes in [RPC](/documents/advanced/rpc).
- Convert `RpcStream` iterators into UI lists and latest signals in [Signals and Streams](/documents/advanced/signal-stream).
- Compare standalone SSE connections in [Server-Sent Events](/documents/advanced/event-source).
