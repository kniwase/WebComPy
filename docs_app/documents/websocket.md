---
title: WebSocket
description: Open bidirectional text connections with use_websocket — connection sharing, exponential backoff with jitter, close introspection, disconnected send buffering, and gap recovery.
---

# WebSocket

`use_websocket()` gives components a full-duplex text channel over WebSockets. Each call returns a `WebSocketHandle` that is both an `AsyncIterator[str]` of incoming text frames and a sender via `.send(text)`. Multiple components connecting to the same URL and subprotocols inside one app share a single underlying socket with automatic reconnection and clean lifecycle detach.

## When to use

- **Need custom bidirectional raw text messaging or binary/wire control** — use `use_websocket()`.
- **Want dataclass schemas and typed metadata (`datetime`, `UUID`, `Decimal`, `Enum`) checked automatically** — use [Typed Realtime](/documents/advanced/typed-realtime).
- **Only need one-way server-to-client streaming** — prefer [Server-Sent Events](/documents/advanced/event-source).
- **Need request/response calls, batching, or cursor-replayed pub/sub streams** — use [RPC over WebSocket](/documents/advanced/rpc-websocket).

## Setup

Call `use_websocket(url)` in component setup, monitor `.state` with `ConnectionState`, and iterate incoming frames inside `@on_mounted`:

```python
from webcompy import ConnectionState, use_computed
from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.elements import html, repeat
from webcompy.realtime import use_websocket
from webcompy.signal import use_reactive_list


@define_component()
def ChatRoom(context: ComponentContext[None]):
    ws = use_websocket("/api/chat")
    messages = use_reactive_list(lambda: [])

    @on_mounted
    async def listen():
        async for text in ws:
            messages.append(text)

    return html.DIV(
        {},
        html.P({}, use_computed(lambda: f"Socket: {ws.state.value.value}")),
        html.BUTTON(
            {"@click": lambda _ev: ws.send("hello!")},
            "Send",
        ),
        html.UL({}, repeat(messages, lambda m: html.LI({}, m))),
    )
```

## Recipes

### Share connections by `(url, protocols)`

Calls to `use_websocket()` with matching `url` and `protocols` within the same app DI scope reuse one underlying socket. Each handle has its own FIFO queue (`max_queue`), and closing one handle only detaches that caller:

```python
chat_a = use_websocket("/api/chat", protocols=("chat.v2",), max_queue=100)
chat_b = use_websocket("/api/chat", protocols=("chat.v2",))  # shares socket with chat_a

other = use_websocket("/api/chat")  # different protocols -> separate socket
```

### Configure reconnection backoff and inspect `CloseInfo`

By default (`reconnect=True`), unexpected drops switch `.state.value` to `ConnectionState.RECONNECTING` and reconnect with jittered exponential backoff. `.last_close` holds a `CloseInfo(code, reason, was_clean)` signal (or `None` before the first close):

```python
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.realtime import use_websocket


@define_component()
def ReconnectingClient(context: ComponentContext[None]):
    ws = use_websocket(
        "/api/live",
        reconnect_base_delay=1.0,
        reconnect_max_delay=30.0,
        reconnect_max_attempts=8,
    )

    @use_computed
    def close_summary():
        info = ws.last_close.value
        if info is None:
            return "Connected cleanly"
        return f"Last close {info.code} (clean={info.was_clean}): {info.reason}"

    return html.P({}, close_summary)
```

Clean closes with code `1000` stop the loop and move `.state.value` to `ConnectionState.CLOSED` instead of reconnecting.

### Buffer sends while connecting or reconnecting

By default (`buffer_while_disconnected=False`), calling `.send(data)` while `.state.value` is `CONNECTING`, `RECONNECTING`, or `CLOSED` emits a `UserWarning` and discards the frame. Set `buffer_while_disconnected=True` to queue outbound text frames FIFO and flush them automatically on reopen (once `CLOSED` permanently, sends still warn and discard):

```python
ws = use_websocket("/api/chat", buffer_while_disconnected=True)
ws.send('{"action": "subscribe"}')  # queued while CONNECTING, flushed on OPEN
```

## The gap/refetch recipe

`use_websocket()` makes no attempt to buffer or replay server events missed while offline. Instead, combine `ConnectionState` tracking with an HTTP snapshot fetch whenever a socket transitions from `RECONNECTING` back to `OPEN`:

```python
from webcompy import ConnectionState
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component
from webcompy.realtime import use_websocket


@define_component()
def ResyncableFeed(context: ComponentContext[None]):
    ws = use_websocket("/api/events")
    was_reconnecting = False

    @ws.state.on_after_updating
    async def on_state_change(new_state: ConnectionState):
        nonlocal was_reconnecting
        if new_state == ConnectionState.RECONNECTING:
            was_reconnecting = True
        elif new_state == ConnectionState.OPEN and was_reconnecting:
            was_reconnecting = False
            snapshot = await HttpClient.get("/api/events/snapshot")
            # merge snapshot.json() into local state
```

If you want server-backed cursor catch-up without writing gap recovery yourself, use `Subscription` and `RpcWsClient` from [RPC over WebSocket](/documents/advanced/rpc-websocket).

### Bridge WebSocket frames with signal streams

Pass a `WebSocketHandle` directly into `to_reactive_list` or `to_signal`:

```python
from webcompy.aio import to_reactive_list
from webcompy.realtime import use_websocket

ws = use_websocket("/api/chat")
log = to_reactive_list(ws, maxlen=100)
```

## Behavior notes

- **Reconnection math**: Delay before attempt $n$ (`attempt >= 1`) is `min(reconnect_max_delay, reconnect_base_delay * 2 ** (attempt - 1)) * random.uniform(0.5, 1.0)`. `attempts` resets to `0` once a connection reaches `ConnectionState.OPEN`.
- **Binary frames**: `use_websocket()` only accepts text frames; arriving binary frames emit a `UserWarning` and are ignored.
- **Per-app DI scoping**: Inside an active app DI scope, connection handles are shared across components using the `(url, protocols)` key and automatically detached on component destroy via chained destroy hooks. Outside a DI scope, `use_websocket()` warns and creates an isolated connection.
- **SSR and hydration**: During SSR and `webcompy generate`, `use_websocket()` logs a warning, returns an already-closed empty handle with `.state.value == ConnectionState.CLOSED` and `.last_close.value is None` whose `.send()` warns and discards, and embeds nothing in `<script id="__webcompy_data__">`.

## Pitfalls

- **Inconsistent `protocols` tuple**: Omitting `protocols` in one component while passing `protocols=("chat.v2",)` in another opens **two** independent sockets, and passing a bare string like `protocols="chat.v2"` raises `TypeError`.
- **Conflicting options on a shared socket**: Only the **first** subscriber's `reconnect`, `reconnect_base_delay`, `reconnect_max_delay`, `reconnect_max_attempts`, and `buffer_while_disconnected` settings take effect for a `(url, protocols)` key. Subsequent subscribers with different values trigger a `UserWarning` and inherit the existing connection's settings.
- **Unbuffered sends before `OPEN`**: Calling `ws.send(...)` immediately inside component setup without `buffer_while_disconnected=True` warns and drops the message because the handshake has not finished yet.

## Next steps

- Add schema checking and automatic field serialization in [Typed Realtime](/documents/advanced/typed-realtime).
- Step up to structured RPC calls and cursor-backed subscriptions in [RPC over WebSocket](/documents/advanced/rpc-websocket).
- Accumulate or collapse message streams in [Signals and Streams](/documents/advanced/signal-stream).
- Compare one-way push transport in [Server-Sent Events](/documents/advanced/event-source).
