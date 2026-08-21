---
title: RPC
description: Typed JSON-RPC over HTTP with WebComPy — call, notify, batch, and finite streaming responses (RpcStream) with per-item typed decoding and cancellation.
---

# RPC

The `webcompy.rpc` module gives you **typed JSON-RPC over HTTP**. Register
procedures on the server, then call them from components with schema-driven
decoding on both sides. On top of ordinary call/response it adds **finite,
call-scoped streaming responses**: a generator-function procedure produces a
bounded stream of typed items consumed with `async for` — over the same HTTP
endpoint (`/_webcompy-rpc`, configured via `app.rpc.set_path`).

## Registration

Register procedures on the app with `app.rpc.register` (or the `@app.rpc.procedure`
decorator):

```python
app.rpc.register("add", _add)

def _add(a: int, b: int = 0) -> int:
    return a + b
```

- Parameters must be typed; positional arrays and keyword objects are both
  accepted. Required parameters have no default.
- Return annotations are required. Non-JSON-native values (e.g. `bytes`,
  `datetime`, `Decimal`, custom types) are encoded with transfer `meta` and
  restored on the client.

## Typed calls

```python
from webcompy.rpc import call

value = await call("add", {"a": 2, "b": 3}, result_type=int)  # -> 5
```

- `result_type` decodes the result with the same typed codec used for
  parameters (`from_json` + transfer `meta`).
- Error responses raise `RpcError` with `code`, `message`, and optional
  `data`.

## Notifications and batches

`notify(method, params)` is fire-and-forget (no `id`, no response). `batch(...)`
sends several calls in one HTTP request:

```python
from webcompy.rpc import batch, notify

await notify("record", {"name": "n1"})
results = await batch([("add", {"a": 1}, int), ("add", {"a": 2}, int)])
```

## Streaming

A **streaming procedure** is a generator function whose return annotation is a
subscripted iterable — an async generator for `AsyncIterator[T]` /
`AsyncIterable[T]`, a sync generator for `Iterator[T]` / `Iterable[T]`. The
element type `T` becomes the result schema:

```python
from collections.abc import AsyncIterator

async def _count_up(n: int) -> AsyncIterator[int]:
    for i in range(1, n + 1):
        yield i

app.rpc.register("count_up", _count_up)
```

Registration rejects unsubscripted annotations (e.g. bare `AsyncIterator`),
non-generator functions with iterable annotations, and generator functions
whose annotation is not one of the four iterable forms.

Consume a stream with `rpc.stream`, which POSTs a `"stream": true` request and
returns an `RpcStream`:

```python
from webcompy.rpc import stream

stream_handle = await stream("count_up", {"n": 5}, result_type=int)

async for item in stream_handle:   # each item decoded as int
    print(item)
```

`RpcStream` is an `AsyncIterator[T]` and also exposes:

- `.state` — a `Signal[RpcStreamState]` (`OPEN` while active, `CLOSED` after
  normal exhaustion or explicit close, `FAILED` when the stream failed).
- `.close()` — idempotent; terminates the stream, aborts the underlying
  fetch, and cancels the server-side generator.
- Context-manager support — `async with stream(...) as s:` closes it on exit.

Mid-stream errors are delivered as an `error` event and surface from
`__anext__` as `RpcError` (carrying `code`, `message`, and `data` when
available); items produced before the error are yielded first. Streams created
inside component setup are closed automatically on component destroy.

The HTTP wire format is Server-Sent Events over the RPC endpoint: one `item`
event per element (`{"data": <encoded>, "meta": <meta or null>}`), a `done`
event on exhaustion, and an `error` event (`{"code", "message", "data"}`) on
mid-stream failure. All pre-stream failures (unknown method, invalid params,
stream-member mismatches, batch entries, notifications) keep ordinary
`application/json` JSON-RPC error responses.

Cancellation: closing the stream aborts the fetch, and the server stops
iterating and closes the generator on client disconnect.

Outside the browser (SSR/SSG), `rpc.stream` issues no network request: it
emits a `UserWarning` and returns an immediately-finished empty stream with
`state == CLOSED`. Stream results are never baked into the hydration payload.

## Non-goals

- Infinite, shared event streams are `register_subscription` /
  `RpcWsClient.subscribe` (see [RPC over WebSocket](./rpc_websocket.md)).
- Streams have no cursor, replay, or rejoin; they fail on disconnect.
- Streaming is not supported in batch requests (each entry is rejected) or
  as notifications (not executed).
