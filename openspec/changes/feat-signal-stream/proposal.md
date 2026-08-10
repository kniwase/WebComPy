# Proposal: feat-signal-stream

## Why

WebComPy is signal-first: state lives in `Signal`/`ReactiveList` cells and the UI reacts automatically. But an important class of data — realtime messages (WebSocket/SSE), progress ticks, and other event streams — has *occurrence* semantics, not *cell* semantics: every arrival matters, including consecutive duplicates. WebComPy's Signal equality contract deliberately suppresses same-value writes, so naively piping events into a Signal silently swallows repeated events. There is currently no sanctioned bridge between the async/iterator world (`async for`, async generators) and the signal world, which blocks the planned realtime composables (`use_event_source`, `use_websocket`) and forces users to hand-roll pump loops, cleanup, and error handling.

## What Changes

- New utility module `webcompy/aio/_stream.py` providing three conversion utilities:
  - `to_signal(source, initial) -> StreamResult[T]` — bridge an `AsyncIterable[T]` (or plain `Iterable[T]`) into a `Signal[T]` with a mandatory initial value (Angular `toSignal(obs, {initialValue})` precedent). Returns a result object with `.value: Signal[T]`, `.error: Signal[Exception | None]`, and `.finished: Signal[bool]` (AsyncResult-style error model).
  - `to_reactive_list(source, *, maxlen=None) -> StreamListResult[T]` — accumulate every item into a `ReactiveList[T]` (chat-log/notification-feed shape), with `.items`, `.error`, `.finished`. Optional `maxlen` keeps the newest N items (drop-oldest, `collections.deque(maxlen=N)` semantics); default is unbounded.
  - `to_async_iter(sig, *, emit_initial=False, maxlen=None) -> AsyncIterator[T]` — bridge a `Signal[T]`'s updates into an async iterator. Each item corresponds to a signal *update* (signal-level dedup applies upstream). Queue is unbounded by default; `maxlen` switches to drop-oldest buffering.
- Lifecycle integration: bridges created inside component setup are torn down automatically on component destroy (same `on_before_destroy` mechanism as the storage composables); standalone usage requires explicit `aclose()`.
- Non-transferable: results of these utilities are derived views and SHALL NOT participate in hydration transfer (same rule as `Computed`).

## Capabilities

### New Capabilities

- `signal-stream`: Bidirectional conversion between signals and (async) iterators — `to_signal`, `to_reactive_list`, `to_async_iter` — including queue semantics (unbounded default, drop-oldest with `maxlen`), error propagation, completion signaling, and lifecycle cleanup.

### Modified Capabilities

(none)

## Impact

- **Code**: new `packages/webcompy/src/webcompy/aio/_stream.py`; public exports in `webcompy/aio/__init__.py`; unit tests under `tests/`.
- **APIs**: additive only (`to_signal`, `to_reactive_list`, `to_async_iter`, `StreamResult`, `StreamListResult`, `StreamAsyncIterator`). No breaking changes.
- **Dependencies**: none (stdlib `asyncio`; existing signal and async-scheduler machinery).
- **Downstream**: foundation for the planned realtime composables (`use_event_source` / `use_websocket`), which will consume transport callbacks via these bridges.
- **Docs**: new section in docs_app covering the signal/stream duality and the three utilities.

## Known Issues Addressed

(none)

## Non-goals

- Realtime composables themselves (`use_event_source`, `use_websocket`) — separate changes building on this one.
- Backpressure beyond drop-oldest capping (no blocking queues, no drop-newest, no error-on-overflow policies).
- Operator pipelines (map/filter/scan-style combinators) — users compose with plain async generators.
- Hydration transfer of streamed values (derived views are client-side only).
- Replay buffers for late subscribers (a `to_async_iter` consumer sees only updates after subscription, unless `emit_initial=True`).
