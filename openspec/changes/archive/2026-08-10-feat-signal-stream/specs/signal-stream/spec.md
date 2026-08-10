# Signal-Stream Specification (delta)

## ADDED Requirements

### Requirement: to_signal shall bridge an iterable source into a Signal with a mandatory initial value

`to_signal(source, initial)` SHALL accept an `AsyncIterable[T]` or a plain `Iterable[T]` and SHALL return a `StreamResult[T]` exposing `.value: Signal[T]` (initialized to `initial`), `.error: Signal[Exception | None]` (initialized to `None`), and `.finished: Signal[bool]` (initialized to `False`). The initial value is mandatory: there SHALL be no default, so the result type is always `Signal[T]` and the UI always has a renderable value before the first item arrives. A single pump task SHALL be scheduled eagerly at creation via the framework's async scheduling path (`aio_run`). As the source yields items, the pump SHALL assign each item to `.value`, making it visible through normal reactivity. Because `.value` is a Signal, the signal equality contract applies: an item equal to the current value SHALL NOT notify consumers (cell semantics, by design).

#### Scenario: Bridging an async generator into a signal

- **WHEN** a component creates `result = to_signal(agen(), 0)` where `agen()` yields `1`, `2`, `3`
- **THEN** `result.value.value` SHALL be `0` immediately after creation
- **AND** as the pump consumes the source, `result.value.value` SHALL become `1`, then `2`, then `3`, with reactive consumers notified on each change

#### Scenario: Equal consecutive items are not re-notified (cell semantics)

- **WHEN** a bridged source yields two consecutive items that compare equal
- **THEN** the second item SHALL be assigned but SHALL NOT trigger change notification, consistent with the signal equality contract
- **AND** users needing every occurrence SHALL use `to_reactive_list` or `to_async_iter` instead

#### Scenario: Source exhaustion marks finished

- **WHEN** the source iterable is exhausted without error
- **THEN** `result.finished.value` SHALL become `True` and `result.error.value` SHALL remain `None`

#### Scenario: Plain sync iterable is accepted

- **WHEN** `to_signal([1, 2, 3], 0)` is called with a plain iterable
- **THEN** the pump SHALL consume it item by item (yielding control between items so the event loop is not starved) and `.value` SHALL settle at `3` with `finished` becoming `True`

### Requirement: to_signal shall surface pump errors via an AsyncResult-style error signal

When the pump raises an exception from the source, `to_signal` SHALL record it on `.error` and set `.finished` to `True`, and SHALL stop pumping. The exception SHALL NOT propagate into the render tree. Cancellation (via `aclose()` or component destroy) SHALL stop the pump silently without setting `.error`.

#### Scenario: Source raises mid-stream

- **WHEN** a bridged async generator yields `1` and then raises `ValueError("boom")`
- **THEN** `result.value.value` SHALL be `1`, `result.error.value` SHALL be the `ValueError` instance, and `result.finished.value` SHALL be `True`

#### Scenario: Cancellation is silent

- **WHEN** `result.aclose()` is called (or the owning component is destroyed) while the pump is waiting on the source
- **THEN** the pump SHALL stop without setting `.error` and without raising into caller code

### Requirement: to_reactive_list shall accumulate items with optional drop-oldest capping

`to_reactive_list(source, *, maxlen=None)` SHALL accept an `AsyncIterable[T]` or `Iterable[T]` and SHALL return a `StreamListResult[T]` exposing `.items: ReactiveList[T]`, `.error: Signal[Exception | None]`, and `.finished: Signal[bool]`. Every source item SHALL be appended to `.items` (occurrence semantics: duplicates are kept). When `maxlen` is an `int`, the list SHALL keep only the newest `maxlen` items by removing from the front (drop-oldest, `collections.deque(maxlen=N)` semantics). When `maxlen` is `None` (default), the list SHALL grow unbounded; this is deliberate and SHALL be documented with guidance to set `maxlen` for long-lived streams. Error, finished, scheduling, and cleanup behavior SHALL match `to_signal`.

#### Scenario: Accumulating a chat log

- **WHEN** a component creates `result = to_reactive_list(ws_messages)` and the source yields `"hi"`, `"hi"`, `"bye"`
- **THEN** `list(result.items)` SHALL equal `["hi", "hi", "bye"]` (duplicate occurrence preserved)

#### Scenario: maxlen keeps the newest N items

- **WHEN** `to_reactive_list(source, maxlen=2)` consumes items `1`, `2`, `3`
- **THEN** `list(result.items)` SHALL equal `[2, 3]`

### Requirement: to_async_iter shall bridge signal updates into an async iterator

`to_async_iter(sig, *, emit_initial=False, maxlen=None)` SHALL return an `AsyncIterator[T]` whose items correspond to *updates* of `sig` observed via `on_after_updating`. Updates are delivered in order, one queue item per update. Writes suppressed by the signal equality contract produce no item. When `emit_initial=True`, the signal's current value SHALL be enqueued once at subscription time before any subsequent update. The internal queue SHALL be unbounded by default; when `maxlen` is an `int` and the queue is full, the oldest queued item SHALL be dropped to make room (drop-oldest). Items produced before subscription SHALL NOT be replayed (other than the `emit_initial` current value). When the iterator is closed (`aclose()` / `async for` abandonment) or the owning component is destroyed, the signal subscription SHALL be removed via `consumer_destroy` so no further items are enqueued and no leak remains.

#### Scenario: Consuming signal updates with async for

- **WHEN** a consumer runs `async for v in to_async_iter(sig)` and `sig.value` is set to `1`, then `2`
- **THEN** the loop body SHALL observe `1` and then `2`, in order

#### Scenario: Equal consecutive writes produce no item

- **WHEN** `sig.value` is set to the same value twice in a row
- **THEN** the iterator SHALL yield at most one item for those writes (signal-level dedup applies upstream)

#### Scenario: emit_initial delivers the current value first

- **WHEN** `to_async_iter(sig, emit_initial=True)` is created while `sig.value == 5`
- **THEN** the first awaited item SHALL be `5`

#### Scenario: Slow consumer with maxlen drops oldest

- **WHEN** `to_async_iter(sig, maxlen=2)` buffers updates `1`, `2`, `3` before the consumer awaits
- **THEN** the consumer SHALL receive `2` and then `3` (oldest dropped)

### Requirement: Bridges created in component setup shall be torn down on component destroy

When any of the three utilities is called during component setup (active component context present), the bridge SHALL register cleanup on the component's `on_before_destroy` lifecycle — chaining with any existing hook as established by the storage composables — so the pump task is cancelled and/or the signal subscription is destroyed automatically. When called outside component setup, the caller SHALL be responsible for calling `aclose()` on the returned object (or iterator). No module-level registries SHALL be introduced (No-New-Globals invariant).

#### Scenario: Component destroy cancels the bridge

- **WHEN** a component creates a bridge in setup and is later destroyed
- **THEN** the pump task SHALL be cancelled (or the subscription removed) and no further updates SHALL be delivered

#### Scenario: Standalone usage requires explicit aclose

- **WHEN** a bridge is created outside any component context and the source is infinite
- **THEN** the bridge SHALL remain active until `aclose()` is called

### Requirement: Bridged results shall not participate in hydration transfer

Signals and lists produced by these utilities are derived client-side views and SHALL NOT be collected for hydration transfer (same rule as `Computed`). During server-side rendering, `to_signal`/`to_reactive_list` with finite sources MAY be pumped by the render context's scheduler, but their results SHALL NOT be serialized into the hydration payload.

#### Scenario: SSG output contains no bridged state

- **WHEN** a page using `to_signal` is statically generated
- **THEN** the hydration payload SHALL NOT contain the bridged signal's value as transferable state
