---
title: Server-Sent Events
description: Receive server-pushed events in WebComPy with use_event_source — connection sharing, queue policy, and reconnection recipes.
---

# Server-Sent Events

Server-Sent Events (SSE) let a server push messages to the browser over a long-lived HTTP connection. WebComPy exposes them through the `use_event_source` composable, which returns a connection handle that is itself an async iterator of `SSEvent` occurrences.

Unlike state (`Signal`) which has cell semantics, SSE messages have *occurrence* semantics: every arrival matters, duplicates included, and nothing is suppressed. `use_event_source` is the network-side counterpart of the `signal-stream` utilities — it yields the raw occurrence stream, and you decide whether to bridge the values into cells.

## Basic usage

```python
from webcompy.realtime import use_event_source

@define_component("sse-alerts")
def Alerts(context):
    alerts = use_event_source("/api/alerts")

    @on_mounted
    async def consume():
        async for event in alerts:
            print(event)  # SSEvent(event="message", data=..., last_event_id=...)
```

Each yielded item is a frozen `SSEvent` dataclass:

| Field | Meaning |
|---|---|
| `event` | The SSE event type (`"message"` by default) |
| `data` | The event payload as text |
| `last_event_id` | The `id:` field sent by the server, if any |

The `events` parameter selects which named SSE event types are delivered; anything else is filtered out:

```python
es = use_event_source("/events", events=("status", "progress"))
```

By default only `("message",)` events are delivered.

`events` must be a non-empty tuple of non-empty strings — a bare string (`events="message"`), an empty tuple, or a non-string element is rejected with a `TypeError`/`ValueError` before any connection is opened.

## POST requests

`use_event_source` opens through the browser-native `EventSource` API by default, which cannot send a request body. Pass `method` (any non-empty string other than `"GET"`), `body`, and `headers` to open a **fetch-based** SSE connection that sends the request body and headers:

```python
es = use_event_source(
    "/query",
    method="POST",
    body='{"q":"x"}',
    headers={"Content-Type": "application/json"},
    events=("result",),
)
```

Fetch-based connections send the given URL unchanged (relative URLs resolve against the document) and parse the `text/event-stream` response incrementally. `body`/`headers` together with `method="GET"` raise a `ValueError` before any connection is opened; a `method` that is not a non-empty string raises a `TypeError`. Non-GET connections require a running event loop (the browser or an `asyncio` context); calling them in a synchronous server context raises a `RuntimeError`.

### Fetch-based reconnection

Fetch-based connections follow EventSource-style auto-reconnect: if the request fails to open, the response status is not successful, the body is not `text/event-stream`, or the body stream ends, the connection transitions to `RECONNECTING` and retries with an exponential backoff (1s base, 30s cap, with jitter) until explicitly closed. Reconnect requests carry the `Last-Event-ID` header once any `id:` has been received, so a server that honors it can resume from where the client left off. Only `.close()` (or the equivalent detachment/component-destroy path) terminates the loop.

### Sharing and filtering for fetch-based connections

Fetch-based connections are keyed by `(url, method, body, normalized headers)`, so identical requests (same body and headers, with header names compared case-insensitively) share a single underlying connection while different bodies or headers never do. The full event stream is read once and each subscriber's requested `events` set is filtered per subscriber — a new subscriber asking for additional event types does **not** reopen the underlying connection.

### Non-goals

- There is no typed SSE composable (`use_typed_event_source` does not exist).
- Reconnection parameters are fixed (1s base / 30s cap); the server's `retry:` field is not honored.
- Events missed during a disconnect are not replayed beyond what `Last-Event-ID` enables server-side.
- There is no server-side SSE endpoint helper; mount your own endpoint (e.g. via `asgi-mount`).

## Connection handle

The handle exposes three surfaces:

- **Iteration** — `async for ev in es:` yields every received event in order.
- `.state` — a `Signal[ConnectionState]` (`CONNECTING` / `OPEN` / `CLOSED`) reflecting the underlying connection.
- `.close()` — detaches **only your own subscription**; it never tears down a connection that other subscribers still use (see below).

## Connection sharing

Within one app, `use_event_source` calls with the same URL share a single underlying native `EventSource`. The first subscriber opens the connection; the last subscriber's close detaches it. Each subscriber receives its own FIFO queue, so a slow consumer never blocks another, and is also free to iterate at its own pace:

```python
# These two calls share ONE underlying connection to /events
feed_a = use_event_source("/events")
feed_b = use_event_source("/events")
```

Sharing matters in practice: browsers enforce a per-domain cap on HTTP/1.1 connections, so a dozen components subscribing to the same endpoint should not open a dozen sockets.

Two calls with the same URL but **different `events` sets** do not share silently: the second call reopens the shared connection with the union of both event types. Events arriving in that close-and-reopen window are lost, and the browser's `Last-Event-ID` resumption starts fresh on the reopened connection — use consistent `events` tuples for a URL to keep the connection stable.

## Queues and slow consumers

Subscriber queues are unbounded by default: events arriving before your code reaches the next `await` accumulate until consumed. For long-lived high-frequency streams, cap a subscriber's backlog with `max_queue`, which keeps only the newest events (drop-oldest):

```python
es = use_event_source("/events", max_queue=100)
```

Capping is per subscriber — one capped consumer does not affect others on the same connection.

`max_queue` must be `None` or an integer greater than or equal to 1; other values raise before any connection is opened.

## Closing

Call `.close()` when the component no longer needs the stream (component-destroy hooks detach automatically for subscriptions created inside component setup; abandoned iterators are cleaned up by the runtime):

```python
es.close()  # idempotent; detaches only this caller
```

## Reconnection and the gap/refetch recipe

The browser's native `EventSource` reconnects automatically and resumes via `Last-Event-ID` where the server supports it. During the outage the handle keeps iterating transparently; `.state` exposes the transitions (`OPEN` → `CONNECTING` → `OPEN`).

SSE does not replay the events missed while disconnected. When `.state` returns to `OPEN`, re-pull the authoritative state yourself:

```python
from webcompy.realtime import ConnectionState
from webcompy.signal import effect

def refetch():
    ...  # re-pull the authoritative state, e.g. a fresh HTTP request

effect(lambda: refetch() if es.state.value == ConnectionState.OPEN else None)
```

Treat `.state` as the signal that a server round-trip is eligible again; keep in-stream events as the incremental updates on top.

## Bridging to signals

Because `use_event_source` yields an async iterable, the `signal-stream` utilities integrate directly. Accumulate every occurrence into a wider `ReactiveList`, or collapse to a single latest value with `to_signal`:

```python
feed = to_reactive_list(use_event_source("/events"), maxlen=50)
# feed.items: ReactiveList[SSEvent]
```

This is the intended path when occurrence semantics are not what the UI needs — see [Signals and Streams](/documents/signal-stream).

## Server-side rendering

During SSR/SSG there is no browser connection: `use_event_source` returns an immediately-finished empty handle whose `.state` is `CLOSED`, and emits a warning. No connection state or received events are transferred into the hydration payload.
