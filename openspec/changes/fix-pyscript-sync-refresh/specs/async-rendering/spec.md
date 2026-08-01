# Delta: async-rendering

## MODIFIED Requirements

### Requirement: Dynamic element refresh shall be async with a sync signal wrapper in _render() only

`RepeatElement._refresh()`, `SwitchElement._refresh()`, and `MarkdownForElement._refresh()` SHALL be `async def` methods.

Signal callback registration SHALL use a sync wrapper method (`_refresh_sync`) ONLY when registered from `_render()`. When registered from `_on_set_parent()` (which runs during element construction, before `_render()`), the raw async `_refresh` SHALL be used instead. This is because:

- `_render()` registers the callback in an async context (`async def _render()`), so the callback registration is intentional and the sync wrapper keeps DOM updates synchronous wherever blocking is possible.
- `_on_set_parent()` runs during component construction (synchronous context). Using the sync wrapper (`_refresh_sync`) with `loop.run_until_complete()` in PyScript interferes with the synchronous signal propagation context — specifically, it can prevent dependent synchronous callbacks (e.g., `Computed` → text element `_update_text`) from executing before the signal setter returns.

The fire-and-forget path for `_on_set_parent()` is safe because:
1. Signal propagation is synchronous: `producer_notify_consumers()` iterates consumers in insertion order
2. Synchronous callbacks (e.g., `Computed` re-evaluation → `_update_text`) complete before async callbacks are dispatched
3. The `_refresh` async callback is dispatched via `_resolve_async_callback()` → in PyScript, `aio_run()` (fire-and-forget); in server/test, `nest_asyncio` + `run_until_complete()`

The sync wrapper SHALL delegate to the shared `_run_refresh_sync(refresh, *args)` helper in `webcompy/elements/types/_dynamic.py` (see the `elements` spec). `_run_refresh_sync` SHALL dispatch the refresh as follows:

- **No running event loop** (all environments): `asyncio.run(refresh(*args))`
- **Running event loop in the Pyodide environment** (`ENVIRONMENT == "pyscript"`): the refresh coroutine SHALL be scheduled on the event loop via `aio_run`, wrapped in a safe coroutine that logs refresh exceptions with a formatted traceback (via `_log_error`). `_run_refresh_sync` SHALL NOT call `loop.run_until_complete` here — Pyodide's webloop raises `RuntimeError: Cannot stack switch` from synchronous JS entrypoints, so blocking would only partially execute the refresh and drop the async remainder
- **Running event loop elsewhere** (CPython server/test): `nest_asyncio.apply(loop)` SHALL be applied conditionally (once per loop), then `loop.run_until_complete(refresh(*args))`

In Pyodide, `nest_asyncio` SHALL NOT be imported or applied. In CPython (server/test), `nest_asyncio.apply()` SHALL be used conditionally to allow nested `run_until_complete()` calls.

`RepeatElement._render()` and `SwitchElement._render()` SHALL continue to call `await self._refresh()` for the initial render path (where the caller is already in an async context).

#### Scenario: RepeatElement refresh triggered by signal update
- **WHEN** a `ReactiveList` value changes and `RepeatElement._refresh()` is triggered via the sync wrapper (`_refresh_sync`)
- **THEN** `_dispatch()` SHALL detect `_is_async = False` (because the wrapper is a sync method) and call it directly
- **AND** `_refresh_sync` SHALL delegate to `_run_refresh_sync(self._refresh, *args)`
- **AND** in non-Pyodide environments, `_run_refresh_sync` SHALL execute `self._refresh()` to completion via `loop.run_until_complete()` before returning
- **AND** in the Pyodide environment, `_run_refresh_sync` SHALL schedule the refresh on the event loop via `aio_run` (fire-and-forget) instead of blocking, so the refresh completes fully without raising "Cannot stack switch"
- **AND** in non-Pyodide environments, child rendering and DOM updates SHALL complete before the signal setter returns

#### Scenario: SwitchElement refresh triggered by signal update (via `_on_set_parent`)
- **WHEN** a `Signal` value changes and `SwitchElement._refresh()` is registered via `_refresh` (async) in `_on_set_parent()`
- **THEN** `_dispatch()` SHALL detect `_is_async = True` and delegate to `_resolve_async_callback()`
- **AND** in browser, `_resolve_async_callback` SHALL dispatch `_refresh` via `aio_run()` (fire-and-forget)
- **AND** in server/test, `_resolve_async_callback` SHALL execute `_refresh` synchronously via `nest_asyncio` + `run_until_complete()`
- **AND** deferred `on_after_rendering` callbacks SHALL be scheduled correctly regardless of environment
- **AND** synchronous dependent callbacks (e.g., `Computed` re-evaluation, text element updates) SHALL complete before the async refresh is dispatched, ensuring DOM consistency

#### Scenario: Dynamic element callback registration differs by code path
- **WHEN** `SwitchElement._on_set_parent()` registers a signal callback
- **THEN** it SHALL register `self._refresh` (async), not `_refresh_sync`, because `_on_set_parent()` runs synchronously during construction and using `_refresh_sync` would cause `loop.run_until_complete()` to interfere with PyScript's synchronous signal propagation context
- **AND** this SHALL hold for both `isinstance(self._cases, SignalBase)` and the per-condition registration paths
- **WHEN** `SwitchElement._render()` registers a signal callback
- **THEN** it SHALL register `self._refresh_sync` (sync wrapper), because `_render()` is itself async and the sync wrapper keeps DOM updates synchronous wherever blocking is possible (non-Pyodide environments)
- **AND** both paths SHALL set `_signal_activated = True` before registering, preventing double registration regardless of which path executes first
- **AND** since `_on_set_parent()` runs during element construction (before `_render()`), `_render()` normally finds `_signal_activated` already True and skips registration — the `_render()` registration path exists mainly for dynamic elements where `_on_set_parent()` may not have run

### Requirement: Async signal callbacks shall execute with environment-dependent semantics

When a signal update triggers a callback registered via `on_after_updating` whose callable is an `async def` (i.e. `CallbackConsumerNode._is_async` is `True`), `_dispatch()` SHALL delegate execution to `_resolve_async_callback()` in `packages/webcompy/src/webcompy/aio/_aio.py`. The execution semantics of `_resolve_async_callback()` SHALL differ by environment in a documented, intentional way:

- **Browser (PyScript)**: async callbacks SHALL be dispatched fire-and-forget via `aio_run()` → `asyncio.ensure_future()`. Async callbacks are NOT guaranteed to complete before the next synchronous statement after the signal setter returns. This is intentional — the browser prioritizes UI responsiveness over completion ordering for user-level async callbacks.
- **Server / test (CPython)**: async callbacks SHALL be executed to completion synchronously via `nest_asyncio` + `loop.run_until_complete()` before the signal setter returns. This is intentional — SSG/SSR and tests need deterministic, in-order completion so that HTML output and assertions are reproducible.

This divergence is a deliberate design decision, not a bug. Dependent changes (e.g. SSG/SSR via `feat-ssg-via-ssr`, data transfer via `feat-hydration-data-transfer`, `Suspense` via `feat-suspense-component`) SHALL rely on this written contract rather than an emergent behavior.

`_refresh_sync` (the sync wrapper used by `RepeatElement` / `SwitchElement` when registered from `_render()`) is NOT an async callback from `_dispatch()`'s viewpoint — `iscoroutinefunction(_refresh_sync)` is `False`, so `_dispatch()` calls it directly and synchronously regardless of environment. The environment-dependent path above applies only to genuinely async callbacks (user-defined async hooks, and the raw `async _refresh` registered from `_on_set_parent()`). The completion semantics of `_refresh_sync` itself SHALL follow `_run_refresh_sync` (see the `elements` spec): synchronous completion in non-Pyodide environments, event-loop scheduling in Pyodide.

#### Scenario: Async user hook triggered by a signal in the browser
- **WHEN** a developer registers `@on_after_updating async def hook(v): ...` on a signal, and the signal's value changes in the browser
- **THEN** `_dispatch()` SHALL detect `_is_async = True` and call `_resolve_async_callback(self._callback, self._producer._value)`
- **AND** the browser SHALL dispatch the hook fire-and-forget via `aio_run()` → `asyncio.ensure_future()`
- **AND** the hook MAY complete after the signal setter has returned
- **AND** synchronous dependent callbacks (e.g. `Computed` re-evaluation → `_update_text`) SHALL still complete before the signal setter returns (because sync callbacks execute first during `producer_notify_consumers`)

#### Scenario: Async user hook triggered by a signal during SSG
- **WHEN** the same hook is triggered during `generate_html()` / `generate_static_site()`
- **THEN** the server SHALL execute the hook to completion synchronously via `nest_asyncio` + `loop.run_until_complete()`
- **AND** the hook SHALL complete before the signal setter returns
- **AND** the resulting HTML SHALL reflect any DOM mutations the hook performed, deterministically

#### Scenario: `_refresh_sync` is treated as a sync callback regardless of environment
- **WHEN** a signal updates and the registered callback is `_refresh_sync` (a sync `def`)
- **THEN** `_dispatch()` SHALL detect `_is_async = False` and call `_refresh_sync(...)` directly
- **AND** `_refresh_sync` SHALL delegate to `_run_refresh_sync`, which SHALL run `self._refresh(...)` to completion via `loop.run_until_complete()` in non-Pyodide environments (server/test uses `nest_asyncio`-patched `run_until_complete`)
- **AND** in the Pyodide environment, `_run_refresh_sync` SHALL schedule `self._refresh(...)` on the event loop via `aio_run` (fire-and-forget) instead of blocking, so the refresh completes on a later event-loop iteration without raising "Cannot stack switch"
- **AND** the DOM update SHALL complete before the signal setter returns in non-Pyodide environments only
