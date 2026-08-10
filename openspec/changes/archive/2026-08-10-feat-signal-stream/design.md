# Design: feat-signal-stream

## Context

WebComPy's reactive core is cell-based: `Signal`/`Computed`/`ReactiveList`/`ReactiveDict` hold *current state* and propagate changes, with an equality contract that suppresses same-value writes. Realtime-style data (WebSocket/SSE messages, progress ticks) has *occurrence* semantics instead: every arrival matters, duplicates included. Cross-framework research (RxJS, Vue/vueuse, Svelte, Angular, React) confirms the split is universal — every ecosystem's latest-value primitive dedups equal consecutive values (`Object.is`/`hasChanged`), and event streams are modeled separately. WebComPy currently has no sanctioned bridge: `aio/` only covers one-shot async (`AsyncResult`, `resolve_async`).

This change adds the bridge layer. It is deliberately transport-agnostic: the planned realtime composables (`use_event_source`/`use_websocket`) will be thin adapters from port callbacks onto these bridges.

Grounded facts (verified in codebase):

- Pump scheduling uses `aio_run(coro)` (`aio/_aio.py`), the same path as `AsyncResult._execute`.
- Signal update subscription: `SignalBase.on_after_updating(fn) -> CallbackConsumerNode` (`signal/_base.py:94`); unsubscribe via `consumer_destroy(node)` (`signal/_graph.py:220`).
- `ReactiveList.pop(index)` exists (`signal/_list.py:39`) for drop-oldest trimming.
- Component-scoped cleanup: `_get_active_component_context()` + `on_before_destroy` hook chaining, as established in `storage/_composable.py:171-193`.

## Goals / Non-Goals

**Goals:**

- Three utilities in `webcompy/aio/_stream.py`:
  - `to_signal(source, initial) -> StreamResult[T]` — async/sync iterable → `Signal[T]`. `initial` is mandatory so the result is `Signal[T]`, never `Signal[T | None]`, and the UI never stalls waiting for the first item.
  - `to_reactive_list(source, *, maxlen=None) -> StreamListResult[T]` — accumulate every item into `ReactiveList[T]`; `maxlen` = keep newest N (drop-oldest).
  - `to_async_iter(sig, *, emit_initial=False, maxlen=None) -> AsyncIterator[T]` — signal updates → async iterator.
- Result objects expose `.error: Signal[Exception | None]` and `.finished: Signal[bool]` (AsyncResult-style error model). `to_async_iter` instead surfaces source errors naturally by raising inside `async for`.
- Queue semantics: unbounded by default (specified in requirements/scenarios); `maxlen` switches to drop-oldest. Uniform rule across `to_reactive_list` and `to_async_iter`.
- Lifecycle: component-setup creation auto-cleans on destroy; standalone creation requires explicit `aclose()`.

**Non-Goals:**

- Realtime composables, replay buffers, operator pipelines, additional backpressure policies (see proposal Non-goals).
- Hydration transfer of bridged values (derived views; same rule as `Computed`).

## Decisions

### D1: Two result objects, AsyncResult-shaped

`StreamResult(value, error, finished)` and `StreamListResult(items, error, finished)` are small generic classes with read-only signal properties. Rationale: mirrors `AsyncResult(state/data/error)` which users already know; keeps error handling out of band so `async for` consumers of the raw iterator and signal consumers of the bridged view each get idiomatic error surfaces. Alternative considered: raising pump errors into the render tree via ErrorBoundary — rejected because a background pump is not part of rendering; an observable error signal is explicit and testable.

### D2: Mandatory `initial` for `to_signal`

Without an initial value the signal would be `T | None` and every consumer would need None-guards; a stalled source would also leave the UI without a renderable value. Angular's `toSignal(obs, {initialValue})` is the direct precedent. Alternative (`initial=None` default) rejected: it reintroduces `None` into the type for a convenience that costs every consumer.

### D3: Pump via `aio_run`, one task per bridge

Each bridge starts exactly one pump task through `aio_run()` (the `AsyncResult` path). The pump owns the full lifecycle: normal exhaustion → `finished=True`; exception → `error` set + `finished=True`; cancellation (aclose/destroy) → silent stop. Rationale: reuses the scheduler-port-aware path that already handles browser/server differences. Alternative (lazy start on first read) rejected: eager start makes `finished`/`error` truthful from creation and matches AsyncResult behavior.

### D4: Drop-oldest via deque semantics, unbounded default

Internal buffer is `asyncio.Queue` (unbounded) or a tiny drop-oldest wrapper (on full: `get_nowait()` then `put_nowait()`). `to_reactive_list` trims with `pop(0)` when exceeding `maxlen`. Rationale: `collections.deque(maxlen=N)` is the canonical Python precedent; unbounded default matches every surveyed ecosystem (RxJS `scan`, React concat, vueuse push) and is documented as a deliberate spec requirement. Slow-consumer memory growth is the accepted trade-off, mitigated by `maxlen` and docs guidance.

### D5: `to_async_iter` delivers *updates*, not writes

Items are enqueued from `on_after_updating`, so signal-level dedup applies upstream (an equal consecutive write never reaches the iterator). This is honest semantics: a Signal is a cell, and its stream view reflects cell changes. `emit_initial=True` enqueues the current value at subscription time (BehaviorSubject-style opt-in); default False (Subject-style) because surprise initial items break `async for` accumulation patterns more often than they help.

### D6: Component-scoped cleanup via existing hook chaining

Reuse the storage pattern: if `_get_active_component_context()` is present at creation, chain an `on_before_destroy` hook that cancels the pump / destroys the consumer node; otherwise the caller must `aclose()`. Rationale: consistency with `sync_tabs`; no new lifecycle machinery; satisfies the No-New-Globals invariant (no module-level registries — per-instance tasks only). Note: pump tasks registered through `aio_run` in a render context are awaited/cancelled by that context's scheduler, which covers server-side teardown.

### D6a: `to_async_iter` abandonment cleanup via weakref-tracked wrapper

CPython 3.12 does not call `aclose()` when an `async for` loop is abandoned with `break` (verified via bytecode: the break path skips `END_ASYNC_FOR`), and leaves a pending `async_generator_athrow` task that keeps the generator — and therefore the signal subscription — alive until loop shutdown (reproduced with a pure-Python minimal case, no WebComPy involved). To satisfy the spec requirement that abandonment removes the subscription, `to_async_iter` returns a small public `StreamAsyncIterator` wrapper (exported from `webcompy.aio`) instead of the raw async generator. The wrapper carries a `weakref.finalize` that runs `_dispose()` (consumer destroy + queue sentinel) as soon as the consumer drops the iterator — which happens promptly when the consuming coroutine's frame is released. Exposing the concrete type also lets type checkers see `aclose()` for standalone cleanup. Explicit `aclose()`, component destroy, and the generator's own `finally` (a guarded no-op once disposed) cover the remaining paths; the underlying generator object may linger until loop shutdown due to the CPython athrow-task behavior, but it is inert (disposed flag set, queue abandoned).

### D7: Sync iterables accepted everywhere

`to_signal`/`to_reactive_list` accept plain `Iterable[T]` too (detect `__aiter__` vs `__iter__`), pumped item-by-item with `await asyncio.sleep(0)` yields so large sync sources don't starve the event loop. Rationale: makes the utilities unit-testable without any async source and costs almost nothing.

## Risks / Trade-offs

- [Unbounded queues can grow without limit under a slow consumer] → Documented in spec requirements/scenarios as deliberate; `maxlen` provides the escape hatch; docs recommend `maxlen` for long-lived streams.
- [Pump exceptions after component destroy could log noisily] → Cancellation is checked before error recording; `asyncio.CancelledError` always stops silently.
- [Users may expect `to_async_iter` to see pre-subscription values] → Spec states subscription-time semantics; `emit_initial` opt-in documented.
- [Duplicate arrivals are invisible through `to_signal` when equal to current value] → This is the documented cell/occurrence distinction; the spec includes a scenario making it explicit so users choose `to_reactive_list`/`to_async_iter` for occurrence semantics.

## Migration Plan

Additive only; no existing code paths change. Rollback = revert the commit.

## Open Questions

(none — queue policy, initial-value, error model, and lifecycle were settled during design discussion)
