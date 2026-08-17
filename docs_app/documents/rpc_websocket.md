---
title: RPC over WebSocket
description: Run typed JSON-RPC calls and server subscriptions over a shared, auto-reconnecting WebSocket with RpcWsClient — cursors, catch-up on reconnect, resync_required, and heartbeat tuning.
---

# RPC over WebSocket

`RpcWsClient` runs the same typed JSON-RPC machinery as the HTTP `rpc` module over a persistent, shared, auto-reconnecting WebSocket. On top of plain call/response it adds **server → client subscriptions** with a Phoenix-style rejoin-and-catch-up protocol, so a dropped connection heals without losing events.

```python
from webcompy.rpc import RpcWsClient

client = RpcWsClient()
```

## Typed calls

`call()` sends a standard JSON-RPC request and resolves the typed result, exactly like the HTTP `rpc.call` (same `meta` member, same schema coercion, same `RpcError` mapping):

```python
value = await client.call("add", {"a": 2, "b": 3}, result_type=int)  # -> 5
```

- Responses are correlated by `id`; error responses raise `RpcError` with `code`, `message`, and `data`.
- A call issued while the connection is not `OPEN` fails fast with `RpcError`.
- Calls **in flight when the connection drops fail** with `RpcError` — they are never silently retried. Retry idempotent operations yourself; the streaming case heals automatically via subscriptions (below).
- `notify(method, params)` is fire-and-forget (no `id`).

The underlying socket is the **shared, reference-counted, auto-reconnecting** connection from `use_websocket`. Multiple `RpcWsClient` instances in one app share a single connection.

## Subscriptions

Register a subscription procedure on the server as an **async generator**:

```python
app.rpc.register_subscription(
    "ticker",
    lambda ticker_id: _ticker(ticker_id),   # see below
)

async def _ticker(ticker_id):
    import asyncio, itertools
    for i in itertools.count(1):
        await asyncio.sleep(0.1)
        yield {"seq": i}
```

Subscribe from the client with `subscribe(method, params, *, event_type=...)`:

```python
sub = client.subscribe("ticker", {"ticker_id": "a"})

async for event in sub:   # each decoded event, in cursor order
    print(event["seq"])
```

- `event_type` is decoded with the same typed codec as realtime messages (`from_json` + transfer `meta`).
- `sub` is an `AsyncIterator[E]` and also exposes:
  - `.state` — a `Signal[RpcSubscriptionState]` (`PENDING` / `ACTIVE` / `RESYNC_REQUIRED` / `CLOSED`).
  - `.last_cursor` — a `Signal[int | None]` tracking the last received server cursor.
- `sub.close()` sends an `_webcompy.unsubscribe` notification and finishes the iterator. Subscriptions are also detached automatically when the owning component is destroyed.

## Reconnect, catch-up, and resync

Each event carries a server-assigned monotonic `cursor`. When the connection drops:

1. The client automatically **re-subscribes every live subscription with its last received cursor**.
2. The server **replays buffered events** (`cursor > last_cursor`) before resuming live delivery — nothing within the replay window is lost, and nothing is delivered twice.
3. If the client's cursor is **older than the server's bounded replay buffer** (default 256 events, configurable at registration), the server answers `resync_required` instead of silently skipping: the client sets `sub.state` to `RESYNC_REQUIRED` and the iterator ends.

```python
async for event in sub:
    ...
    if sub.state.value == RpcSubscriptionState.RESYNC_REQUIRED:
        # the replay buffer overflowed: refetch authoritative state and resubscribe fresh
        await refetch_snapshot()          # your own state fetch (e.g. rpc.call)
        sub = client.subscribe("ticker", {"ticker_id": "a"})
        break
```

The replay buffer is bounded per stream to keep server memory in check; overflow is always signalled honestly — never a silent gap. Subscription streams are shared per `(method, params)` and kept alive for a grace period after the last subscriber leaves, so catch-up works across short outages.

## Server-driven reconnection

Send the reserved `_webcompy.close` notification to ask the server to close the socket abnormally (code `1011`), which engages the reconnect loop — useful for rolling restarts or forcing clients to rejoin:

```python
await client.notify("_webcompy.close")
```

Reserved `_webcompy.*` method names cannot be registered as user procedures.

## Heartbeat

Browser WebSockets expose no protocol ping/pong, so liveness detection is application-level. `RpcWsClient` sends a `_webcompy.ping` notification every `heartbeat_interval` (default `30.0`s) and expects any server frame within `heartbeat_timeout` (default `10.0`s). If none arrives, it force-closes the socket abnormally so the reconnect loop engages — this detects TCP-idle connections that look open but are dead.

```python
client = RpcWsClient(
    heartbeat_interval=30.0,   # seconds between pings
    heartbeat_timeout=10.0,    # max silence before an abnormal close
)
```

Pass `heartbeat_interval=None` to disable the heartbeat. The server always answers `_webcompy.ping` with `_webcompy.pong`.

## SSR / SSG

`RpcWsClient` is browser-runtime-only. During SSR/SSG it emits a warning and performs **no socket work**; SSR-time RPC continues to use the HTTP client and transfer cache. No subscription state, cursors, or in-flight calls are transferred in the hydration payload.

## See also

- [WebSocket](/documents/websocket) — the underlying `use_websocket` transport.
- [Typed Realtime](/documents/typed-realtime) — the typed message codec used for events.
