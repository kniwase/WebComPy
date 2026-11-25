---
title: Signals and Streams
description: Bridge occurrence-based async streams and reactive cell state — choose between cells and occurrences, convert feeds with to_signal and to_reactive_list, and stream signal updates with to_async_iter.
---

# Signals and Streams

WebComPy distinguishes **cells** (`Signal`, `Computed`, `ReadonlySignal`) from **occurrence streams** (`AsyncIterable`, SSE, WebSocket, and streaming RPC feeds). Cells represent the latest value and collapse consecutive equal writes; occurrence streams deliver every event in order, duplicates included. The stream helpers in `webcompy.aio` (`to_signal`, `to_reactive_list`, `to_async_iter`) bridge the two models with automatic lifecycle cleanup.

## Choosing between cells and streams

| Primitive / helper | Model | Duplicate handling | Typical use |
|---|---|---|---|
| [`use_state`](/documents/basic/reactive-state) / `Signal` | Writable cell | Equal writes suppressed | UI toggles, counters, form fields (SSR-transferable) |
| [`use_readonly_signal`](/documents/advanced/readonly-signal) / `use_window_event` | Read-only cell | Equal writes suppressed | Service status, viewport size, visibility state |
| `to_signal(source, initial)` | Stream -> latest cell | Latest item stored in `.value` (cell semantics) | Progress indicators, latest telemetry reading |
| `to_reactive_list(source, maxlen=...)` | Stream -> ordered list | Keeps every occurrence in arrival order | Chat logs, activity feeds, token buffers |
| `to_async_iter(sig, emit_initial=False, maxlen=...)` | Cell -> async stream | Fires only when `sig` changes to a distinct value | Debounced API search, background worker queues |

## When to use

- **Need a component-owned value backed by an async feed** — use `to_signal` for a single latest reading or `to_reactive_list` for an accumulating history.
- **Need an async loop to react whenever a signal updates** — use `to_async_iter(signal)` inside an async worker instead of polling or wiring manual callbacks.
- **Directly opening network connections or RPC calls** — pair these helpers with [Server-Sent Events](/documents/advanced/event-source), [WebSocket](/documents/advanced/websocket), or [RPC Streaming](/documents/advanced/rpc-streaming).

## Setup

All three converters live in `webcompy.aio`. `to_signal` and `to_reactive_list` begin consuming the iterable immediately when called inside component setup and cancel automatically on component destroy:

```python
from webcompy import use_computed
from webcompy.aio import to_reactive_list, to_signal
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.realtime import use_websocket


@define_component()
def TelemetryPanel(context: ComponentContext[None]):
    ws = use_websocket("/api/telemetry")
    latest = to_signal(ws, initial="waiting...")
    history = to_reactive_list(ws, maxlen=20)

    return html.DIV(
        {},
        html.P({}, use_computed(lambda: f"Latest: {latest.value.value}")),
        html.UL(
            {},
            repeat(history.items, lambda msg: html.LI({}, msg)),
        ),
    )
```

## Recipes

### Accumulate an SSE or WebSocket feed with a bounded window

`to_reactive_list(source, *, maxlen=None)` appends every emitted item to `.items` (`ReactiveList[T]`), preserving duplicates, and drops the oldest entry once `len(result.items) > maxlen`. You can also observe `.finished` and `.error`:

```python
from webcompy import use_computed
from webcompy.aio import to_reactive_list
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.realtime import use_event_source


@define_component()
def AuditLog(context: ComponentContext[None]):
    feed = to_reactive_list(use_event_source("/api/audit"), maxlen=50)

    return html.DIV(
        {},
        html.P(
            {},
            use_computed(
                lambda: f"Error: {feed.error.value}"
                if feed.error.value is not None
                else ("Stream closed" if feed.finished.value else "Streaming...")
            ),
        ),
        html.UL(
            {},
            repeat(feed.items, lambda ev: html.LI({}, f"[{ev.event}] {ev.data}")),
        ),
    )
```

### Track the latest item and stream status with `to_signal()`

`to_signal(source, initial)` updates `.value` (`Signal[T]`) as each item arrives, sets `.finished` (`Signal[bool]`) to `True` on normal exhaustion or error, and records any exception in `.error` (`Signal[Exception | None]`):

```python
from webcompy import use_computed
from webcompy.aio import to_signal
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


async def count_steps():
    yield "Validating..."
    yield "Uploading..."
    yield "Done"


@define_component()
def JobProgress(context: ComponentContext[None]):
    step = to_signal(count_steps(), initial="Idle")

    return html.SPAN(
        {},
        use_computed(
            lambda: f"{step.value.value} (done={step.finished.value})"
        ),
    )
```

### React to signal writes sequentially with `to_async_iter()`

`to_async_iter(sig, *, emit_initial=False, maxlen=None)` turns writes to a `Signal` into an async iterator (`StreamAsyncIterator[T]`). Passing `emit_initial=True` yields the current `sig.value` first before waiting for subsequent updates:

```python
from webcompy import use_state
from webcompy.aio import to_async_iter
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.elements import html


@define_component()
def SearchWatcher(context: ComponentContext[None]):
    query = use_state(lambda: "")
    summary = use_state(lambda: "Type to search")

    @on_mounted
    async def watch_queries():
        async for q in to_async_iter(query, emit_initial=False, maxlen=1):
            if not q:
                summary.value = "Type to search"
                continue
            resp = await HttpClient.get("/api/search", query_params={"q": q})
            summary.value = resp.text if resp.ok else f"Error {resp.status_code}"

    return html.DIV(
        {},
        html.INPUT({"@input": lambda ev: setattr(query, "value", ev.target.value)}),
        html.P({}, summary),
    )
```

Notice `maxlen=1`: when the user types faster than HTTP requests finish, older queued queries are dropped so the loop always inspects the newest query next.

## Behavior notes

- **Queueing and eviction policy**:
  - `to_reactive_list(..., maxlen=N)` appends arriving items in order and pops index `0` whenever length exceeds `N` (unbounded when `maxlen=None`).
  - `to_async_iter(..., maxlen=N)` uses a bounded **drop-oldest** queue — if the consumer falls behind, oldest buffered values are evicted so the next iteration yields fresh state.
- **Lifecycle and manual cleanup**: All three helpers register a chained `on_before_destroy` cleanup hook when called inside component setup, so tearing down a component stops background consumption and detaches signal listeners automatically. When calling `to_signal`, `to_reactive_list`, or `to_async_iter` outside component setup, hold onto the returned handle and call `await handle.aclose()` to release the task/subscription cleanly.
- **Equality deduplication at cell boundaries**: `to_async_iter(signal)` listens to `on_after_updating`, which only fires when `signal.value = new` changes the signal according to equality. Likewise, assigning each streamed item to `StreamResult.value` in `to_signal` skips notifying dependents if the new item equals the previous one.
- **SSR and hydration**: When fed from closed server handles (such as SSR `use_event_source` or `use_websocket`), `to_signal` and `to_reactive_list` see immediate exhaustion (`finished.value == True`). None of the three converters serialize stream state into the SSR hydration payload.

## Pitfalls

- **Unbounded list growth**: Leaving `maxlen=None` on a long-lived `to_reactive_list(use_websocket(...))` chat or telemetry feed lets memory grow indefinitely during a session. Set `maxlen=` to a concrete UI cap.
- **Expecting repeat triggers in `to_async_iter()`**: Writing `count.value = count.value` triggers no update on `to_async_iter(count)`. If every identical click or ping must fire an event, emit directly into an async queue or callback instead of writing to a `Signal`.
- **Closing outside component setup**: Using `.close()` does not exist on `StreamResult`, `StreamListResult`, or `StreamAsyncIterator` — the cleanup method is `await handle.aclose()`.

## Next steps

- Expose external callbacks as read-only cells in [Read-only Signals and Events](/documents/advanced/readonly-signal).
- Open shared SSE and WebSocket streams in [Server-Sent Events](/documents/advanced/event-source) and [WebSocket](/documents/advanced/websocket).
- Review reactive primitives (`Signal`, `ReactiveList`, `use_state`) in [Reactive State](/documents/basic/reactive-state).
- Full API: [Data, Forms & i18n API](/documents/api/data).
