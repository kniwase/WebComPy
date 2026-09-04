---
title: RPC
description: Typed JSON-RPC over HTTP with WebComPy — Procedure contracts, RpcHttpClient, batch, notify, and finite streaming responses (RpcStream) with per-item typed decoding and cancellation.
---

# RPC

The `webcompy.rpc` module gives you **typed JSON-RPC over HTTP** via declarative contracts. Define `Procedure` objects in a shared schema module, bind implementations with `app.rpc.bind`, and invoke them from components through `RpcHttpClient` with schema-driven decoding on both sides.

## Schema and binding

Create a schema module:

```python
from dataclasses import dataclass
from webcompy.rpc import Procedure

@dataclass
class AddParams:
    a: int
    b: int = 0

add = Procedure("add", AddParams, int)
```

Register implementations on the app with `bind` (or `@app.rpc.bind(contract)`):

```python
def _add(p: AddParams) -> int:
    return p.a + p.b

app.rpc.bind(add, _add)
```

`bind` validates that the implementation's parameter and return annotations match the contract's declared types. Parameters must be typed dataclasses; return annotations are required.

## Typed calls

```python
from webcompy.rpc import RpcHttpClient

client = RpcHttpClient()
value: int = await add(client, AddParams(a=2, b=3))  # -> 5
```

`Procedure` invocation returns an `RpcCall[P, R]` (`Awaitable[R]`). `await` performs the call via the transport; the transport owns encoding (`encode_with_meta`) and decoding (`from_json` with `meta`). Error responses raise `RpcError` with `code`, `message`, and optional `data`.

## Notifications and batches

`notify` is fire-and-forget (no `id`, no response). `batch` sends several `RpcCall`s in one HTTP request:

```python
from webcompy.rpc import batch, notify

await notify(add(client, AddParams(a=1)))  # one id-less POST

c1 = add(client, AddParams(a=1))
c2 = add(client, AddParams(a=2))
results: tuple[int, int] = await batch(c1, c2)  # one POST array
empty: tuple[()] = await batch()    # no I/O
```

Each `RpcCall` can only be consumed once — after `notify` or `batch` uses it, awaiting it again raises `RuntimeError`. Create a fresh call for each statement.

`batch` supports heterogeneous tuple inference (`tuple[R1, R2, ...]` via `0..6` overloads) and `return_exceptions=True` to surface per-call `RpcError`s as `R | RpcError` entries.

## Streaming

A **streaming procedure** is a generator function whose return annotation is a subscripted iterable — an async generator for `AsyncIterator[T]` / `AsyncIterable[T]`, a sync generator for `Iterator[T]` / `Iterable[T]`. The element type `T` becomes the result schema:

```python
from collections.abc import AsyncIterator
from webcompy.rpc import StreamingProcedure

count_up = StreamingProcedure("count_up", CountUpParams, int)

async def _count_up(p: CountUpParams) -> AsyncIterator[int]:
    for i in range(1, p.n + 1):
        yield i

app.rpc.bind(count_up, _count_up)
```

Consume a stream via the contract, which delegates to the transport's `stream`:

```python
stream_handle = count_up(client, CountUpParams(n=5))

async for item in stream_handle:   # each item decoded as int
    print(item)
```

`RpcStream` is an `AsyncIterator[T]` with `.state` (`OPEN`/`CLOSED`/`FAILED`), `.close()` (idempotent, cancels server generator), and context-manager support. Mid-stream errors surface as `RpcError`. Streams created inside component setup are closed automatically on component destroy.

The HTTP wire is Server-Sent Events: one `item` event per element, `done` on exhaustion, `error` on failure. All pre-stream failures keep ordinary `application/json` error responses. Cancellation aborts the fetch and stops the server generator.

Outside the browser (SSR/SSG), the stream helper warns and returns an immediately-finished empty stream with `state == CLOSED`. Stream results are never baked into the hydration payload.

## Non-goals

- Infinite, shared event streams are `Subscription` / `RpcWsClient` subscriptions (see [RPC over WebSocket](/documents/advanced/rpc-websocket)).
- Streams have no cursor, replay, or rejoin; they fail on disconnect.
- Streaming is not supported in batch requests or as notifications.
