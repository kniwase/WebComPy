---
title: Server-Sent Events
description: Stream unidirectional server events into WebComPy components with use_event_source — shared registries, named event filtering, POST streaming, Last-Event-ID resumption, and SSR degradation.
---

# Server-Sent Events

Server-Sent Events (SSE) push a continuous stream of text events from your server over standard HTTP. `use_event_source()` returns an `EventSourceHandle` that behaves as an `AsyncIterator[SSEvent]`, shares connections cleanly across components in the same app, supports both browser-native `EventSource` (`GET`) and streaming `fetch` requests (`POST`), and degrades safely during SSR and static generation.

## When to use

- **Need server-to-client push with automatic reconnect and named events** — use `use_event_source()`.
- **Need bidirectional client-to-server messaging as well** — use [WebSocket](/documents/advanced/websocket) (or [Typed Realtime](/documents/advanced/typed-realtime)).
- **Running a finite, single-request typed RPC generator (such as LLM token generation for one prompt)** — use [RPC Streaming](/documents/advanced/rpc-streaming).
- **Performing a one-shot JSON fetch** — use [`HttpClient` and `use_async_result`](/documents/basic/http-and-async).

## Setup

Call `use_event_source(url)` in component setup and bridge it with `to_reactive_list` (or iterate in `@on_mounted`):

```python
from webcompy import ConnectionState, use_computed
from webcompy.aio import to_reactive_list
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.realtime import use_event_source


@define_component()
def EventFeed(context: ComponentContext[None]):
    es = use_event_source("/api/events")
    feed = to_reactive_list(es, maxlen=50)

    return html.DIV(
        {},
        html.P({}, use_computed(lambda: f"State: {es.state.value.value}")),
        html.UL(
            {},
            repeat(feed.items, lambda ev: html.LI({}, ev.data)),
        ),
    )
```

Each yielded `SSEvent` is a frozen dataclass with three string attributes: `event` (defaults to `"message"`), `data`, and `last_event_id`.

## Recipes

### Subscribe to named event types and track connection state

Pass `events=(...)` as a non-empty tuple of event names and observe `es.state.value` against `ConnectionState` (`CONNECTING`, `OPEN`, `RECONNECTING`, `CLOSED`):

```python
from webcompy import ConnectionState, use_computed
from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.elements import html
from webcompy.realtime import use_event_source
from webcompy.signal import use_state


@define_component()
def DeployMonitor(context: ComponentContext[None]):
    es = use_event_source("/api/deploy/stream", events=("progress", "done"))
    status = use_state(lambda: "Waiting")

    @on_mounted
    async def read_events():
        async for ev in es:
            if ev.event == "progress":
                status.value = f"Step: {ev.data}"
            elif ev.event == "done":
                status.value = f"Finished ({ev.data}) [id={ev.last_event_id}]"
                es.close()

    return html.DIV(
        {},
        html.SPAN(
            {},
            use_computed(lambda: "Live" if es.state.value == ConnectionState.OPEN else es.state.value.value),
        ),
        html.P({}, status),
    )
```

### Share one connection across components

Inside the same app DI scope, multiple `use_event_source("/api/events")` calls share a single underlying connection. Each caller gets its own `EventSourceHandle` and independent FIFO queue (`max_queue`), so a slow consumer never blocks another:

```python
# In StatusWidget
status_es = use_event_source("/api/stream", events=("status",), max_queue=32)

# In MetricsWidget mounted in the same app
metrics_es = use_event_source("/api/stream", events=("metrics",))
```

For `GET` connections, when a second subscriber requests an event name not yet subscribed (`"metrics"`), the shared browser connection automatically reopens listening to the union `("status", "metrics")`. Calling `status_es.close()` detaches only `status_es` and keeps the shared socket open until `metrics_es` also closes or unmounts.

### Stream `POST` SSE endpoints (e.g., AI prompts or filtered queries)

Pass `method="POST"` along with `body=` and `headers=` to use WebComPy's streaming `FetchPort` transport instead of the browser's GET-only `EventSource` API:

```python
import json

from webcompy.aio import to_reactive_list
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.realtime import use_event_source


@define_component()
def SummaryStream(context: ComponentContext[None]):
    es = use_event_source(
        "/api/summarize",
        method="POST",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"doc_id": 42}),
        events=("token", "done"),
    )
    tokens = to_reactive_list(es)

    return html.DIV(
        {},
        repeat(tokens.items, lambda ev: html.SPAN({}, ev.data)),
    )
```

Fetch-based SSE connections are keyed in the shared registry by `(url, method, body, normalized_headers)` (with lowercased header names) and filter `events` per subscriber on the client without reopening the request when another subscriber asks for another event type.

## Behavior notes

- **Reconnection and `Last-Event-ID`**:
  - With `method="GET"`, native browser `EventSource` manages automatic reconnection and sends the `Last-Event-ID` header automatically after a drop.
  - With non-`GET` methods (e.g. `POST`), WebComPy reconnects automatically using exponential backoff with random jitter (`min(30.0, 1.0 * 2 ** (attempt - 1)) * random.uniform(0.5, 1.0)`), carrying the most recent non-empty `id:` field in the `Last-Event-ID` header.
- **Lifecycle cleanup**: When called inside component setup, `use_event_source()` registers a chained `on_before_destroy` hook calling `handle.close()`. Only the last remaining subscriber closes the underlying browser connection.
- **Testing & standalone usage**: Outside a component context, `.close()` can still be called explicitly, and a `weakref.finalize` fallback detaches abandoned handles on GC. When called outside an active app DI scope, `use_event_source()` warns and opens an unshared connection.
- **SSR and hydration**: On the server and during `webcompy generate`, `ServerEventSourcePort` (for `GET`) and `ServerFetchPort` return an immediately exhausted handle with `state.value == ConnectionState.CLOSED`, emit a warning, and transfer nothing into `<script id="__webcompy_data__">`.

## Pitfalls

- **Passing `body` or `headers` with `method="GET"`**: `use_event_source()` raises `ValueError` immediately if `body` or `headers` is supplied alongside `method="GET"`, because native `EventSource` cannot carry custom headers or a request body.
- **Passing a bare string for `events=`**: `events="message"` raises `TypeError` — always pass a tuple such as `events=("message",)`.
- **Expecting `Last-Event-ID` replay without server support**: Reconnection only replays missed events if your server assigns `id:` fields on emitted SSE frames and honors the incoming `Last-Event-ID` header.
- **Proxy buffering stalling delivery**: Reverse proxies and CDNs often buffer small HTTP chunks until compressed or flushed. Serve SSE endpoints with `Content-Type: text/event-stream`, disable compression on that route, and include `X-Accel-Buffering: no` where needed.
- **Closing a handle cancels only your subscription**: Calling `.close()` inside one component does not force-close the server stream if another component still holds a subscription to the same shared connection.

## Next steps

- Use full-duplex text channels in [WebSocket](/documents/advanced/websocket) or schema-validated frames in [Typed Realtime](/documents/advanced/typed-realtime).
- Convert SSE streams into UI state in [Signals and Streams](/documents/advanced/signal-stream).
- Stream finite, request-scoped generator outputs via [RPC Streaming](/documents/advanced/rpc-streaming).
- Review basic request/response fetching in [HTTP & Async](/documents/basic/http-and-async).
- Full API: [Data, Forms & i18n API](/documents/api/data).
