---
title: Signals and Streams
description: Convert realtime data streams into reactive state with to_signal, to_reactive_list, and to_async_iter.
---

# Signals and Streams

WebComPy state primitives are **cells**: `Signal`, `Computed`, and `ReactiveList` hold *current state* and propagate changes, with an equality contract that suppresses same-value writes. Realtime data (WebSocket/SSE messages, progress ticks) has **occurrence** semantics instead: every arrival matters, duplicates included. The `webcompy.aio` stream utilities bridge these two worlds.

## to_signal: one-shot values

The `to_signal` utility pumps an `AsyncIterable` (or plain `Iterable`) into a `Signal`. The initial value is mandatory so the UI always has a renderable value before the first item arrives:

```python
from webcompy.aio import to_signal

result = to_signal(progress_ticks(), 0)
# result.value: Signal[int]  — updated per item
# result.error: Signal[Exception | None]
# result.finished: Signal[bool]
```

Because the bridge target is a `Signal`, the cell equality contract applies: an item equal to the current value does not notify consumers. Use `to_reactive_list` or `to_async_iter` when every occurrence matters.

## to_reactive_list: accumulating feeds

Chat logs, notification feeds, and event histories accumulate *every* item, duplicates included:

```python
from webcompy.aio import to_reactive_list

feed = to_reactive_list(ws_messages, maxlen=100)
# feed.items: ReactiveList[str]  — newest 100 items
# feed.error: Signal[Exception | None]
# feed.finished: Signal[bool]
```

Set `maxlen` to keep only the newest N items (drop-oldest). Without it the list grows unbounded, which is deliberate but SHALL be capped for long-lived streams. Each append and each trim triggers a reactive update, so a small `maxlen` on a high-frequency source increases notification churn; size `maxlen` to match the source rate.

## to_async_iter: consuming signal updates

The `to_async_iter` utility bridges a `Signal`'s updates into an async iterator. Each item corresponds to a signal *update* (signal-level dedup applies upstream):

```python
from webcompy.aio import to_async_iter

async for value in to_async_iter(count, emit_initial=True):
    await handle(value)
```

Items produced before subscription are not replayed; pass `emit_initial=True` to enqueue the current value first. `maxlen` caps the internal buffer with drop-oldest semantics for slow consumers.

## Queue policy and lifecycle

Buffers are unbounded by default; a slow consumer lets the queue grow, so long-lived streams should set `maxlen`. Bridges created inside component setup are torn down automatically on component destroy; standalone usage requires an explicit `aclose()` call:

```python
result = to_signal(infinite_source(), 0)
...
await result.aclose()  # stop pumping
```

Bridged values are derived client-side views and never participate in hydration transfer (same rule as `Computed`).