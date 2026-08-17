---
title: WebSocket
description: Open bidirectional text connections with use_websocket — connection sharing, reconnection with backoff, close introspection, and disconnected send policy.
---

# WebSocket

WebSockets give you a bidirectional, full-duplex text channel between the browser and a server. WebComPy exposes them through the `use_websocket` composable, which returns a connection handle that is itself an async iterator of text messages.

Like SSE messages, WebSocket messages have *occurrence* semantics: every frame matters, duplicates included, and nothing is suppressed.

## Basic usage

```python
from webcompy.realtime import use_websocket

@define_component("chat")
def Chat(context):
    ws = use_websocket("/api/chat")

    @on_mounted
    async def consume():
        async for message in ws:
            print(message)  # each received text frame
```

`ws.send(data)` sends one text frame. Combined, the handle gives you a full round trip:

```python
ws.send("hello")          # send a text frame
async for message in ws:  # receive text frames
    ...
```

The `protocols` parameter passes subprotocols to the server (see [Connection sharing](#connection-sharing)):

```python
ws = use_websocket("/api/chat", protocols=("chat.v2",))
```

Binary frames sent by the server are ignored with a warning; only text frames are delivered.

## Connection handle

The handle exposes four surfaces:

- **Iteration** — `async for message in ws:` yields every received text message in arrival order.
- `.state` — a `Signal[ConnectionState]` (`CONNECTING` / `OPEN` / `RECONNECTING` / `CLOSED`) reflecting the underlying connection.
- `.last_close` — a `Signal[CloseInfo | None]` holding a frozen `CloseInfo` for the most recent close event, or `None` if the connection has never closed.
- `.send(data)` — sends one text frame (see [Sending while disconnected](#sending-while-disconnected)).
- `.close()` — detaches **only your own subscription**; it never tears down a connection that other subscribers still use.

| `CloseInfo` field | Meaning |
|---|---|
| `code` | The WebSocket close code (e.g., `1000` normal, `1006` abnormal, `1011` server error) |
| `reason` | The close reason string sent by the server |
| `was_clean` | Whether the close handshake completed cleanly |

`.last_close` is updated on *every* close of the underlying connection — including closures that reconnection later recovers — and is **not** reset when the connection reopens. It is the reliable way to inspect why the socket dropped:

```python
effect(lambda: handle_last_close(ws.last_close.value))
```

## Connection sharing

Within one app, `use_websocket` calls with the same URL **and the same `protocols`** share a single underlying socket. The first subscriber opens the connection; the last subscriber's close detaches it. Each subscriber receives its own FIFO queue, so a slow consumer never blocks another:

```python
# These two calls share ONE underlying socket to /api/chat
chat_a = use_websocket("/api/chat")
chat_b = use_websocket("/api/chat")
```

Different `protocols` values select different application protocols, so they never share:

```python
one = use_websocket("/api/chat", protocols=("chat.v2",))
two = use_websocket("/api/chat")  # a separate socket
```

Reconnection settings (`reconnect`, the backoff delays, `reconnect_max_attempts`, `buffer_while_disconnected`) are properties of the shared connection, not of individual subscribers: the **first** call's settings win, and later calls with the same URL and protocols reuse that connection's settings. If a later call specifies different reconnection settings, a `UserWarning` is emitted and the existing connection's settings remain in effect.

## Reconnection

Unlike the native `EventSource`, a native `WebSocket` does **not** reconnect automatically — the framework owns the reconnect loop. When the underlying socket closes abnormally (any close other than a clean `1000` or a user `.close()`), the shared connection schedules a reconnect with exponential backoff and jitter:

```python
ws = use_websocket("/api/chat", reconnect_base_delay=1.0, reconnect_max_delay=30.0)
```

The delay before attempt *n* is `min(max_delay, base_delay * 2 ** (n-1))` seconds multiplied by a random jitter factor in `[0.5, 1.0]` (so the first retry lands in `[0.5, 1.0]` s, the second in `[1.0, 2.0]` s, then `2–4`, `4–8`, capped at the max). During a backoff wait or in-flight attempt, `.state` is `RECONNECTING`; on success it returns to `OPEN` and iteration continues transparently.

| Parameter | Default | Meaning |
|---|---|---|
| `reconnect` | `True` | Set `False` to fail once and stop |
| `reconnect_base_delay` | `1.0` | Base backoff in seconds |
| `reconnect_max_delay` | `30.0` | Backoff cap in seconds |
| `reconnect_max_attempts` | `None` | `None` = unlimited; an `int` stops after that many failed attempts with `.state == CLOSED` |

No reconnect happens after a **user-initiated `.close()`**, after a **clean `1000` close**, or when `reconnect=False` (a single failure transitions to `CLOSED`). If you want a shared connection to reconnect on every drop, have the server close with a non-`1000` code.

## Sending while disconnected

`ws.send(data)` while the connection is not `OPEN` warns and discards the message by default — the framework refuses to silently queue data during an outage:

```python
ws.send("hello")  # while RECONNECTING → warns and drops, unless buffering is enabled
```

With `buffer_while_disconnected=True`, disconnected sends are buffered FIFO (unbounded — a long outage queues as much memory as you send) and flushed in order on the next transition to `OPEN`. The buffer is discarded if the connection reaches a terminal `CLOSED`. If ordering matters, wait for `.state == OPEN` before sending.

## The gap/refetch recipe

Reconnection does **not** replay messages missed while disconnected (server-side replay is opt-in and out of scope). When `.state` returns to `OPEN`, re-pull the authoritative state yourself — exactly as with SSE:

```python
from webcompy.realtime import ConnectionState
from webcompy.signal import effect

def refetch():
    ...  # re-pull the authoritative state, e.g. a fresh HTTP request

effect(lambda: refetch() if ws.state.value == ConnectionState.OPEN else None)
```

## Bridging to signals

Because `use_websocket` yields an async iterable, the `signal-stream` utilities integrate directly. Accumulate messages into a `ReactiveList`, or collapse to a single latest value with `to_signal`:

```python
feed = to_reactive_list(use_websocket("/api/chat"), maxlen=50)
# feed.items: ReactiveList[str]
```

See [Signals and Streams](/documents/signal-stream).

## Server-side rendering

During SSR/SSG there is no browser connection: `use_websocket` returns an immediately-finished empty handle whose `.state` is `CLOSED`, whose `.last_close` is `None`, and whose `.send()` warns and discards, and emits a warning. No connection state, close info, or messages are transferred into the hydration payload.