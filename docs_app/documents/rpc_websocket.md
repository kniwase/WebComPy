---
title: RPC over WebSocket
description: Run typed RPC calls, batches, notifications, and cursor-replayed subscriptions over a single shared auto-reconnecting WebSocket with RpcWsClient.
---

# RPC over WebSocket

`RpcWsClient` brings the contract API (`Subscription`, `Procedure`, `StreamingProcedure`, `batch`, and `notify`) onto a single shared, auto-reconnecting WebSocket connection. It pairs FIFO per-subscription ordering and automatic cursor catch-up after network drops with optional application-level heartbeats to detect half-open connections.

## When to use

- **Need live server-pushed feeds that resume cleanly across network drops** — use `Subscription` + `RpcWsClient`.
- **Running one-shot queries or pre-rendered SSR fetches** — use [`RpcHttpClient`](/documents/advanced/rpc) (and [RPC Contracts](/documents/advanced/rpc-contracts)).
- **Need finite call-scoped streams (over either HTTP or WebSocket)** — see [RPC Streaming](/documents/advanced/rpc-streaming).
- **Exchanging ad-hoc messages without RPC procedures or cursor replay** — use [WebSocket](/documents/advanced/websocket) or [Typed Realtime](/documents/advanced/typed-realtime).

## Setup

Define a `Subscription` contract, bind an `async def` generator (`AsyncIterator[Event]`) on `app.rpc`, and mount `create_rpc_ws_endpoint(app.rpc)` (done automatically by `webcompy start` / `webcompy serve` at `/_webcompy-rpc` whenever `app.rpc.has_procedures` is `True`):

```python
# Shared contracts + server setup + Starlette mount
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute

from webcompy import WebComPyApp
from webcompy.rpc import Subscription
from webcompy_server.rpc import create_rpc_ws_endpoint


@dataclass
class RoomParams:
    room: str


@dataclass
class RoomMessage:
    sender: str
    text: str


room_events = Subscription("chat.events", RoomParams, RoomMessage, replay_size=256)

# On server app (webcompy start mounts this automatically at app.rpc.path):
# @app.rpc.bind(room_events)
# async def stream_room(params: RoomParams) -> AsyncIterator[RoomMessage]:
#     async for msg in room_bus.subscribe(params.room):
#         yield msg
#
# When embedding inside a custom Starlette host:
# host = Starlette(routes=[WebSocketRoute(app.rpc.path, create_rpc_ws_endpoint(app.rpc))])
```

On the client, instantiate `RpcWsClient()` inside component setup and pass it to `room_events(client, params)` — subscriptions started while connecting are queued automatically and sent as soon as the handshake finishes:

```python
# Client component consuming the subscription
from webcompy import ConnectionState, use_computed
from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.elements import html, repeat
from webcompy.rpc import RpcWsClient
from webcompy.signal import use_reactive_list


@define_component()
def RoomFeed(context: ComponentContext[None]):
    client = RpcWsClient()
    sub = room_events(client, RoomParams(room="general"))
    messages = use_reactive_list(lambda: [])

    @on_mounted
    async def read_room():
        async for msg in sub:
            messages.append(msg)

    return html.DIV(
        {},
        html.P({}, use_computed(lambda: f"WS: {client.state.value.value} / sub: {sub.state.value.value}")),
        html.UL({}, repeat(messages, lambda m: html.LI({}, f"{m.sender}: {m.text}"))),
    )
```

## Recipes

### Recover cleanly with cursor rejoin and `RESYNC_REQUIRED`

Every delivered event updates `sub.last_cursor` (`Signal[int | None]`). When the underlying socket reconnects, `RpcWsClient` automatically re-subscribes carrying `last_cursor` so the server replays missed events from its ring buffer (`replay_size`). If the client stayed disconnected too long and events were evicted, `sub.state.value` transitions to `RpcSubscriptionState.RESYNC_REQUIRED` — refetch an authoritative snapshot via `Procedure` and open a fresh subscription:

```python
# Server: snapshot Procedure + event Subscription
from collections.abc import AsyncIterator
from dataclasses import dataclass

from webcompy.rpc import Procedure, Subscription


@dataclass
class FeedParams:
    channel: str


@dataclass
class FeedSnapshot:
    items: list[str]


@dataclass
class FeedItem:
    id: str
    body: str


get_snapshot = Procedure("feed.snapshot", FeedParams, FeedSnapshot)
watch_feed = Subscription("feed.watch", FeedParams, FeedItem, replay_size=500)


@app.rpc.bind(get_snapshot)
async def handle_snapshot(params: FeedParams) -> FeedSnapshot:
    return FeedSnapshot(items=[])


@app.rpc.bind(watch_feed)
async def handle_watch(params: FeedParams) -> AsyncIterator[FeedItem]:
    async for item in alert_bus.subscribe(params.channel):
        yield item
```

```python
# Client: monitor RESYNC_REQUIRED -> refetch via HTTP + resubscribe
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.rpc import RpcHttpClient, RpcSubscriptionState, RpcWsClient

http_client = RpcHttpClient()


@define_component()
def ResyncableSubscription(context: ComponentContext[None]):
    ws_client = RpcWsClient()
    sub = watch_feed(ws_client, FeedParams(channel="alerts"))

    @sub.state.on_after_updating
    async def handle_state(state: RpcSubscriptionState):
        if state == RpcSubscriptionState.RESYNC_REQUIRED:
            snapshot = await get_snapshot(http_client, FeedParams(channel="alerts"))
            sub.close()
            # Replace UI list from snapshot.items and open a new watch_feed(ws_client, ...)

    return html.DIV({}, "Subscribed")
```

### Multiplex `Procedure`, `batch`, and `notify` over `RpcWsClient`

Once `client.state.value == ConnectionState.OPEN`, pass the same `RpcWsClient` instance to `Procedure` calls, `batch(...)`, and `notify(...)`:

```python
# Server registration
from dataclasses import dataclass
from webcompy.rpc import Procedure


@dataclass
class SendMsgParams:
    room: str
    text: str


@dataclass
class Ack:
    ok: bool


send_message = Procedure("chat.send", SendMsgParams, Ack)


@app.rpc.bind(send_message)
async def handle_send(params: SendMsgParams) -> Ack:
    return Ack(ok=True)
```

```python
# Client usage on an OPEN RpcWsClient
from webcompy import ConnectionState
from webcompy.rpc import RpcError, RpcWsClient, batch, notify

# Inside an async handler when client.state.value == ConnectionState.OPEN:
async def post_messages(ws_client: RpcWsClient) -> None:
    try:
        ack = await send_message(ws_client, SendMsgParams(room="general", text="hi"))
        a1, a2 = await batch(
            send_message(ws_client, SendMsgParams(room="general", text="one")),
            send_message(ws_client, SendMsgParams(room="general", text="two")),
        )
        await notify(send_message(ws_client, SendMsgParams(room="general", text="silent")))
    except RpcError as err:
        print("WS RPC failed:", err.code, err.message)
```

### Tune heartbeat and reconnection backoff

`RpcWsClient` shares `use_websocket()` reconnection options and layers an application-level ping/pong heartbeat on top (`ping` every `heartbeat_interval` seconds; if no frame arrives within `heartbeat_timeout` seconds while `OPEN`, WebComPy forces an abnormal close with code `4000` so reconnection engages):

```python
# Server WS endpoint stays unchanged (handles _webcompy.ping / _webcompy.pong automatically)
# Host custom endpoint: WebSocketRoute(app.rpc.path, create_rpc_ws_endpoint(app.rpc))
```

```python
# Client configuration
from webcompy.rpc import RpcWsClient

client = RpcWsClient(
    heartbeat_interval=20.0,  # set None to disable heartbeat pings
    heartbeat_timeout=5.0,
    reconnect_base_delay=1.0,
    reconnect_max_delay=30.0,
    reconnect_max_attempts=10,
    max_queue=256,
)
```

### Run finite `StreamingProcedure` calls over WebSocket

Passing an `RpcWsClient` to a `StreamingProcedure` multiplexes call-scoped stream items (`stream_id`) over the open socket without blocking concurrent calls or subscriptions:

```python
# Server registration
from collections.abc import AsyncIterator
from dataclasses import dataclass

from webcompy.rpc import StreamingProcedure


@dataclass
class BuildParams:
    target: str


@dataclass
class BuildLine:
    text: str


stream_build = StreamingProcedure("build.stream", BuildParams, BuildLine)


@app.rpc.bind(stream_build)
async def handle_build(params: BuildParams) -> AsyncIterator[BuildLine]:
    yield BuildLine(text=f"Building {params.target}...")
    yield BuildLine(text="Done")
```

```python
# Client iteration over an OPEN RpcWsClient
stream = stream_build(client, BuildParams(target="docs"))
async for step in stream:
    print(step.text)
```

See [RPC Streaming](/documents/advanced/rpc-streaming) for lifecycle states, early cancellation, and SSR degradation.

## Behavior notes

- **Shared socket & ordering**: `RpcWsClient` delegates its transport to [`use_websocket()`](/documents/advanced/websocket) targeting `url or app.rpc.endpoint_url`, so multiple clients in one app reuse a single connection. Server writes pass through a single per-connection FIFO queue, guaranteeing strict `subscribe ack -> buffered replay -> live events` delivery order.
- **Subscription lifecycle (`RpcSubscriptionState`)**:
  - `PENDING` — waiting for server confirmation.
  - `ACTIVE` — confirmed and delivering events (`sub.last_cursor` tracks the latest cursor).
  - `RESYNC_REQUIRED` — replay buffer overflowed on reconnect (`sub.last_cursor` exceeded retention).
  - `CLOSED` — unsubscribed or client closed (`sub.close()` is idempotent and sends unsubscribe).
- **No silent call retries**: Unlike `Subscription` auto-rejoin, in-flight `Procedure` calls never silently retry across disconnects — if the socket drops mid-call, pending calls reject immediately with `RpcError` so mutations cannot accidentally run twice.
- **Malformed/invalid frames**: Decode failures or malformed control frames update `client.last_error` (`Signal[Exception | None]`) instead of tearing down active subscriptions.
- **Lifecycle cleanup & standalone usage**: Creating `RpcWsClient` or calling `.subscribe()` / `sub(client, params)` inside component setup chains cleanup automatically onto `on_before_destroy`. If you instantiate `RpcWsClient()` at module scope or in a long-lived service, call `client.close()` explicitly on teardown.
- **SSR and hydration**: `RpcWsClient` is browser-runtime-only. During SSR and `webcompy generate`, constructing `RpcWsClient()` emits a `UserWarning`, performs no socket work (`state.value == ConnectionState.CLOSED`), returns closed empty iterators for subscriptions/streams, and fails any `call()`/`notify()` with `RpcError`. Never embed `RpcWsClient` data calls for SSR pre-rendering; use [`RpcHttpClient`](/documents/advanced/rpc) for SSR-baked initial data.

## Pitfalls

- **Calling `.call()` / `.notify()` / `.stream()` before `OPEN`**: While `sub(client, params)` queues safely during `CONNECTING`, calling `await proc(client, params)` before `client.state.value == ConnectionState.OPEN` raises `RpcError` immediately.
- **Using `RpcWsClient` for initial SSR data**: SSR will emit a warning and skip all socket calls. Load initial state via `RpcHttpClient` (`Procedure`) and subscribe with `RpcWsClient` for live updates afterward.
- **Small `replay_size` without `RESYNC_REQUIRED` handling**: Once a burst exceeds `replay_size` while a client is offline, events are gone from the server buffer; always handle `RpcSubscriptionState.RESYNC_REQUIRED` by refetching state via `Procedure`.
- **Leaking module-level clients**: Always call `client.close()` when instantiating `RpcWsClient` outside component setup, otherwise the shared socket, reader task, and heartbeat loop stay alive until app teardown.

## Next steps

- Learn finite call-scoped RPC streams in [RPC Streaming](/documents/advanced/rpc-streaming).
- Review declarative contracts and server binding rules in [RPC Contracts](/documents/advanced/rpc-contracts).
- Compare HTTP transport and SSR caching in [RPC](/documents/advanced/rpc).
- Understand the underlying socket registry and typed wire codecs in [WebSocket](/documents/advanced/websocket) and [Typed Realtime](/documents/advanced/typed-realtime).
- Full API: [Server, CLI, RPC & Ports API](/documents/api/server-and-cli).
