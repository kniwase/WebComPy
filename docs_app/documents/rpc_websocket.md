---
title: RPC over WebSocket
description: Run typed JSON-RPC calls and server subscriptions over a shared, auto-reconnecting WebSocket with RpcWsClient — contracts, cursors, catch-up on reconnect, resync_required, and heartbeat tuning.
---

# RPC over WebSocket

`RpcWsClient` runs the same typed JSON-RPC machinery as the HTTP module over a persistent, shared, auto-reconnecting WebSocket via declarative contracts. Define `Procedure`/`Subscription`/`StreamingProcedure` objects in a shared schema module and invoke them through the transport.

```python
from webcompy.rpc import RpcWsClient

client = RpcWsClient()
```

## Typed calls via contracts

Define a `Procedure` contract and invoke it through the transport via `RpcCall`:

```python
from dataclasses import dataclass
from webcompy.rpc import Procedure

@dataclass
class AddParams:
    a: int
    b: int = 0

add = Procedure("add", AddParams, int)

value: int = await add(client, AddParams(a=2, b=3))  # -> 5
```

- Responses are correlated by `id`; error responses raise `RpcError` with `code`, `message`, and `data`.
- A call issued while the connection is not `OPEN` fails fast with `RpcError`.
- Calls **in flight when the connection drops fail** with `RpcError` — they are never silently retried.
- Fire-and-forget `notify` is available as `await notify(add(client, AddParams(a=1)))` — an id-less envelope, no response.

`batch` sends several `RpcCall`s as a single array frame:

```python
from webcompy.rpc import batch

c1 = add(client, AddParams(a=1))
c2 = add(client, AddParams(a=2))
results: tuple[int, int] = await batch(c1, c2)
```

The underlying socket is the **shared, reference-counted, auto-reconnecting** connection from `use_websocket`. Multiple `RpcWsClient` instances in one app share a single connection.

## Subscriptions via contracts

Register a subscription procedure on the server as an **async generator** bound to a `Subscription` contract:

```python
from webcompy.rpc import Subscription

@dataclass
class TickerParams:
    ticker_id: str

@dataclass
class Tick:
    seq: int

ticker = Subscription("ticker", TickerParams, Tick)

async def _ticker(p: TickerParams) -> AsyncIterator[Tick]:
    import asyncio, itertools
    for i in itertools.count(1):
        await asyncio.sleep(0.1)
        yield Tick(seq=i)

app.rpc.bind(ticker, _ticker)
```

Subscribe from the client through the contract:

```python
sub = ticker(client, TickerParams(ticker_id="a"))

async for event in sub:   # each decoded Tick, in cursor order
    print(event.seq)
```

- `event_type` is decoded with the same typed codec as realtime messages (`from_json` + transfer `meta`).
- `sub` is an `AsyncIterator[E]` and also exposes:
  - `.state` — a `Signal[RpcSubscriptionState]` (`PENDING` / `ACTIVE` / `RESYNC_REQUIRED` / `CLOSED`).
  - `.last_cursor` — a `Signal[int | None]` tracking the last received server cursor.
- `sub.close()` sends an `_webcompy.unsubscribe` notification and finishes the iterator. Subscriptions are also detached automatically when the owning component is destroyed.

Create the `RpcWsClient` inside component setup so the subscriptions and the shared socket are released automatically on component destroy. When the client is held outside a component (e.g. a module-level service), call `client.close()` explicitly to release the connection.

## Reconnect, catch-up, and resync

Each event carries a server-assigned monotonic `cursor`. When the connection drops:

1. The client automatically **re-subscribes every live subscription with its last received cursor** (a subscription that has not received any event yet rejoins with cursor `0`).
2. The server **replays buffered events** (`cursor > last_cursor`) before resuming live delivery — nothing within the replay window is lost, and nothing is delivered twice.
3. If the client's cursor is **older than the server's bounded replay buffer** (default 256 events, configurable via `Subscription(..., replay_size=...)`), the server answers `resync_required` instead of silently skipping: the client sets `sub.state` to `RESYNC_REQUIRED` and the iterator ends.

```python
async for event in sub:
    ...
if sub.state.value == RpcSubscriptionState.RESYNC_REQUIRED:
    await refetch_snapshot()
    sub = ticker(client, TickerParams(ticker_id="a"))
```

The replay buffer is bounded per stream to keep server memory in check; overflow is always signalled honestly — never a silent gap. Subscription streams are shared per `(method, params)` and kept alive for a grace period after the last subscriber leaves, so catch-up works across short outages.

## Server-driven reconnection

Send the reserved `_webcompy.close` notification to ask the server to close the socket abnormally (code `1011`), which engages the reconnect loop — useful for rolling restarts. Use the low-level transport `notify` for this reserved method (outside contracts):

```python
await client.notify("_webcompy.close")
```

Reserved `_webcompy.*` method names cannot be registered as user procedures.

## Heartbeat

`RpcWsClient` sends a `_webcompy.ping` notification every `heartbeat_interval` (default `30.0`s) and expects any server frame within `heartbeat_timeout` (default `10.0`s). If none arrives, it force-closes the socket abnormally so the reconnect loop engages.

```python
client = RpcWsClient(
    heartbeat_interval=30.0,
    heartbeat_timeout=10.0,
)
```

Pass `heartbeat_interval=None` to disable the heartbeat. The server always answers `_webcompy.ping` with `_webcompy.pong`.

## Streaming calls via contracts

Streaming procedures — generator functions annotated `-> AsyncIterator[T]` / `AsyncIterable[T]` (async) or `-> Iterator[T]` / `Iterable[T]` (sync) — also work over the WebSocket when exposed as a `StreamingProcedure` contract. A call with `"stream": true` is answered with a `stream_id`, and each element is delivered as a `_webcompy.event` frame.

```python
from webcompy.rpc import StreamingProcedure

count_up = StreamingProcedure("count_up", CountUpParams, int)

stream_handle = count_up(client, CountUpParams(n=5))

async for item in stream_handle:
    print(item)
```

`StreamingProcedure` invocation returns the same `RpcStream` as the HTTP case — an `AsyncIterator[T]` with `.state` (`OPEN` / `CLOSED` / `FAILED`), idempotent `.close()`, and `async with` support. `.close()` sends a `_webcompy.stream_cancel` notification that stops the server-side generator.

Per-call streams are never shared, replayed, or rejoined: each call runs its own generator instance. If the connection drops, an active stream **fails** with `RpcError` from iteration. Streams are not supported in batch requests and notifications targeting streaming procedures are not executed.

## SSR / SSG

`RpcWsClient` is browser-runtime-only. During SSR/SSG it emits a warning and performs **no socket work**; SSR-time RPC continues to use `RpcHttpClient` and the transfer cache. No subscription state, cursors, or in-flight calls are transferred in the hydration payload.

## See also

- [RPC Contracts](/documents/advanced/rpc-contracts) — the declarative contract layer.
- [RPC](/documents/advanced/rpc) — HTTP transport via `RpcHttpClient`.
- [WebSocket](/documents/advanced/websocket) — the underlying `use_websocket` transport.
- [Typed Realtime](/documents/advanced/typed-realtime) — the typed message codec used for events.
