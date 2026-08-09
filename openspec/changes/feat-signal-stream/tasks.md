# Tasks: feat-signal-stream

## 1. Internal stream machinery

- [ ] 1.1 Create `packages/webcompy/src/webcompy/aio/_stream.py` with the shared internals: drop-oldest queue wrapper (unbounded `asyncio.Queue` by default; on `maxlen`, `get_nowait()` + `put_nowait()` when full), sync/async source detection (`__aiter__` vs `__iter__`), and a pump runner built on `aio_run()` that records `error`/`finished` and treats `asyncio.CancelledError` as silent stop
- [ ] 1.2 Implement component-scoped cleanup helper: register pump cancellation on `on_before_destroy` when `_get_active_component_context()` is present, chaining with any existing hook (mirror `storage/_composable.py`'s `_register_destroy_unregister`); expose `aclose()` for standalone usage

## 2. Public utilities

- [ ] 2.1 Implement `StreamResult[T]` (`.value` / `.error` / `.finished` read-only signal properties, `aclose()`) and `to_signal(source, initial)` per spec (mandatory initial, eager pump, sync-iterable support with `await asyncio.sleep(0)` between items)
- [ ] 2.2 Implement `StreamListResult[T]` (`.items` / `.error` / `.finished`, `aclose()`) and `to_reactive_list(source, *, maxlen=None)` with front-trim via `ReactiveList.pop(0)` when exceeding `maxlen`
- [ ] 2.3 Implement `to_async_iter(sig, *, emit_initial=False, maxlen=None)`: subscribe via `on_after_updating`, optional initial enqueue, drop-oldest when bounded, and `consumer_destroy` on iterator close

## 3. Unit tests (`tests/test_signal_stream.py`, browserless)

- [ ] 3.1 `to_signal`: initial value before first item; per-item updates with reactivity; equal-consecutive suppression (cell semantics); sync iterable source; `finished` on exhaustion
- [ ] 3.2 `to_signal` error model: source exception lands on `.error` with `finished=True`; `aclose()` and component-destroy cancellation stop silently (no `.error`)
- [ ] 3.3 `to_reactive_list`: occurrence accumulation including duplicates; `maxlen=2` keeps newest two; unbounded default
- [ ] 3.4 `to_async_iter`: ordered delivery of updates; dedup upstream; `emit_initial=True` yields current value first; `maxlen` drop-oldest for slow consumers; subscription removed after `aclose()` (no further enqueues)
- [ ] 3.5 Lifecycle: bridge created inside a component context (TestRenderer) is torn down on component destroy; standalone bridge requires explicit `aclose()`

## 4. Public API and docs

- [ ] 4.1 Export `to_signal`, `to_reactive_list`, `to_async_iter`, `StreamResult`, `StreamListResult` from `webcompy/aio/__init__.py` (and top-level `webcompy` if that is the established re-export pattern)
- [ ] 4.2 Add a docs_app section explaining cell-vs-occurrence semantics, the three utilities, the unbounded-default queue policy, and the `maxlen` guidance for long-lived streams

## 5. Validation

- [ ] 5.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 5.2 `uv run pyright` passes
- [ ] 5.3 `uv run python -m pytest tests/ --tb=short -q` passes (full suite, no regressions)
- [ ] 5.4 `openspec validate feat-signal-stream` passes
