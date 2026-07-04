# Proposal: Signal Value Transfer

## Why

After `feat-suspense-and-hydration-data-transfer`, the server-to-browser transfer mechanism covers `AsyncResult` states and `FetchPort` response caches. However, application-level `Signal` values computed during SSR are not serialized. Components that derive UI state directly from `Signal` values (not via `AsyncResult`) experience a **flash of default values** during hydration — the browser re-initializes signals with their defaults and only converges to the correct state when user interaction or async data updates them.

The current workaround is to wrap Signal-derived state in `Suspense` or `ClientOnly` boundaries, but this is a developer burden and doesn't cover all cases (e.g., UI toggles, cached computations, form state initialized from server data).

This change extends the hydration data transfer to include Signal values. The `SignalReceivable.__signal_members__` mechanism already auto-tracks all Signal instances assigned to a component's `self` attributes — no explicit registration boilerplate is needed. Signal values (including `Computed` cached values) are collected, encoded via the codec engine (`feat-transfer-codec`), and restored on the browser after component setup.

## What Changes

- **MODIFIED** `packages/webcompy/src/webcompy/signal/_container.py` — `SignalReceivable.__signal_members__` SHALL change from `WeakValueDictionary` keyed by `id(value)` to a regular `dict` keyed by attribute name. `__set_signal_member__` SHALL accept the attribute name parameter (passed from `__setattr__`). `computed_property` SHALL integrate with the name-based registry (it already stores `instance.__dict__[name]`).
- **MODIFIED** `packages/webcompy/src/webcompy/hydration/_collect.py` — `collect_transfer_data()` SHALL traverse `__signal_members__` on each `Component` in the render tree, collecting Signal/Computed/ReactiveList/ReactiveDict values. Each value SHALL be encoded via `encode()` from `webcompy.hydration._codec`.
- **MODIFIED** `packages/webcompy/src/webcompy/hydration/_payload.py` — `TransferPayload` gains a `signals: dict[str, dict[str, Any]]` field mapping component ID to `{attr_name: encoded_value}`. `__webcompy_transfer_version__` bumps to `2`.
- **NEW** `packages/webcompy/src/webcompy/hydration/_restore.py` — `restore_signal_values(component, signals_data)` restores Signal values by directly setting `_value` on each Signal instance (bypassing `set_value()` to avoid triggering notifications). `Computed` cached values are restored the same way (option 2: transfer cached value, skip recompute).
- **MODIFIED** `packages/webcompy/src/webcompy/app/_app.py` — `app.run()` SHALL read `payload.signals` and restore values after component setup.
- **MODIFIED** `packages/webcompy/src/webcompy/app/_root_component.py` — After SSR rendering completes (before `collect_transfer_data`), Signal values SHALL be collected from the component tree.

## Capabilities

### New Capabilities

- `signal-value-transfer`: Server-to-browser transfer of Signal values (`Signal`, `Computed`, `ReactiveList`, `ReactiveDict`) via the hydration data payload. Values are collected automatically from `__signal_members__` (no explicit registration), encoded via the codec engine, and restored on the browser after component setup. `Computed` cached values are transferred as-is (no recompute on restore).

### Modified Capabilities

- `hydration-data-transfer`: `TransferPayload` gains a `signals` section and bumps to version 2. The payload schema is forward-compatible (version 1 browsers ignore the `signals` section).
- `reactive`: `SignalReceivable.__signal_members__` changes key type from `id()` to attribute name. `Computed` instances registered via `computed_property` are included by name.
- `components`: After browser component setup, Signal values from the transfer payload SHALL be restored to the component's Signal instances before the first render.
- `async-rendering`: The collection of Signal values SHALL occur after `await_pending()` completes (so async-resolved values are captured), and before `ctx.dispose()`.

## Known Issues Addressed

- **Flash of default Signal values during hydration** — Components that store UI state in `Signal` instances (not `AsyncResult`) showed default values until user interaction or async updates. This change transfers the SSR-computed values to the browser, eliminating the flash.

## Non-goals

- **Local (non-`self`) Signal variables** — Signals created as local variables in component setup (`count = Reactive(0)`) without being assigned to `self` are NOT captured by `__signal_members__` and are NOT transferred. This matches the existing tracking scope. A future change could add an explicit registration API, but this is out of scope.
- **Signal value restoration triggering notifications** — Restore sets `_value` directly, bypassing `set_value()`. Downstream `Computed` signals that depend on restored sources do NOT automatically recompute. This is acceptable because `Computed` cached values are also transferred (option 2). When a source Signal changes via user interaction, the normal reactive graph handles propagation.
- **Signal graph dependency serialization** — The reactive dependency graph (producer/consumer edges) is NOT transferred. It is rebuilt naturally during browser component setup.
- **Payload compression** — gzip/brotli compression is `feat-payload-compression`.
- **Changing `useAsyncResult` API** — `useAsyncResult` is unchanged; it transparently benefits from transfer data via existing mechanisms.

## Dependencies

- **Requires** `feat-transfer-codec` — Signal values SHALL be encoded/decoded via the codec engine. Without the codec, only plain JSON-serializable values could be transferred, severely limiting usefulness.
- **Benefits from** `feat-async-scheduler-port` — The collection of Signal values occurs after `await_pending()` completes. The scheduler port ensures all async-resolved Signal values are captured before collection.

## Impact

- **Affected modules**:
  - `packages/webcompy/src/webcompy/signal/_container.py` (`__signal_members__` key type change)
  - `packages/webcompy/src/webcompy/hydration/_collect.py` (Signal value collection)
  - `packages/webcompy/src/webcompy/hydration/_payload.py` (`signals` section, version 2)
  - `packages/webcompy/src/webcompy/hydration/_restore.py` (new — value restoration)
  - `packages/webcompy/src/webcompy/hydration/__init__.py` (export restore function)
  - `packages/webcompy/src/webcompy/app/_app.py` (browser restore)
  - `packages/webcompy/src/webcompy/app/_root_component.py` (SSR collection)
- **Breaking**: `__signal_members__` internal key type changes from `int` (id) to `str` (attribute name). This is an internal API; no public consumers use the key directly. `__purge_signal_members__()` iterates `.values()`, which is unaffected by the key change.
- **Backward compatible**: Existing components without Signal-based state work unchanged. Payload version 2 includes a `signals` section that version 1 browsers ignore.
- **Testing**: Unit tests for Signal value collection, encoding round-trip, restoration, and Computed cached value transfer. E2E tests verifying no flash of default values during hydration.
