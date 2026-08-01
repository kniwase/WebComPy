## Why

Signal-driven refresh in dynamic containers (`RepeatElement`, `SwitchElement`, `MarkdownForElement`) is dispatched through `_run_refresh_sync`, which calls `loop.run_until_complete(refresh())` when an event loop is running. In Pyodide (PyScript), a DOM event handler is a synchronous JS entrypoint, and Pyodide's webloop refuses to stack-switch from it: `run_until_complete` raises `RuntimeError: Cannot stack switch because the Python entrypoint was a synchronous function`. The refresh coroutine only executes its synchronous prefix (up to the first `await`), the rest is silently dropped, and the exception surfaces as a pageerror in the browser console — every list mutation or switch toggle from a click in a PyScript app is only half-applied.

## What Changes

- `_run_refresh_sync` (`packages/webcompy/src/webcompy/elements/types/_dynamic.py`) gains a Pyodide-specific branch: instead of blocking on `loop.run_until_complete`, the refresh coroutine is scheduled on the event loop via `aio_run` (the same mechanism `_resolve_async_callback` already uses for async signal callbacks), wrapped so exceptions are logged with a formatted traceback via `_log_error` instead of propagating into the JS event handler.
- Non-Pyodide environments keep the current behavior exactly (`asyncio.run` without a running loop; `nest_asyncio` + `run_until_complete` with one), preserving the synchronous-refresh guarantee that unit tests and `TestRenderer` rely on.
- No public API changes; `DynamicElement._render`/`_hydrate_node` and the container refresh bodies are untouched.

## Capabilities

### New Capabilities

### Modified Capabilities

- `elements`: Add a requirement pinning that synchronous refresh dispatch in the Pyodide environment schedules the refresh on the event loop (completing it fully) instead of blocking on `run_until_complete`, while non-Pyodide environments keep synchronous completion.
- `async-rendering`: Update two requirements that pinned `run_until_complete`-in-both-environments refresh semantics ("Dynamic element refresh shall be async with a sync signal wrapper in _render() only" and "Async signal callbacks shall execute with environment-dependent semantics") to the Pyodide event-loop scheduling semantics.

## Known Issues Addressed

- **"Cannot stack switch" RuntimeError on every signal-driven refresh in PyScript apps**: DOM event handlers are synchronous Pyodide entrypoints; `loop.run_until_complete` raises and the refresh coroutine's async remainder never runs, leaving the DOM half-updated and logging a Python traceback (pageerror). Reproduced in the docs todo demo (`test_todo_remove_done_items` captures the pageerror).

## Non-goals

- Coalescing or deduplication of queued refreshes (rapid successive mutations schedule one refresh each; each reconciles from the current signal value, last-state-wins). A coalescing mechanism is a separate concern.
- Changing refresh semantics in non-Pyodide environments (server rendering, tests, `TestRenderer`).
- Any change to hydration, `_hydrate_node`, or the refresh bodies themselves.

## Impact

- **Code**: `packages/webcompy/src/webcompy/elements/types/_dynamic.py` — one branch in `_run_refresh_sync` (~8 lines).
- **Specs**: `openspec/specs/elements/spec.md` (delta: one ADDED requirement with two scenarios) and `openspec/specs/async-rendering/spec.md` (delta: two MODIFIED requirements whose pinned `run_until_complete`-in-both-environments wording is updated to the Pyodide scheduling semantics).
- **Tests**: new `tests/test_run_refresh_sync.py` (Pyodide scheduling, error logging, non-Pyodide synchronous path); `e2e/docs/test_todo.py::test_todo_remove_done_items` extended to assert no `pageerror` occurred during the interaction, and immediate `is_visible()` checks in `test_todo_add_item`/`test_todo_remove_done_items` updated to Playwright auto-waiting `expect` assertions (Pyodide refreshes are now asynchronous). Full unit suite and full e2e suite re-run.
- **Risk**: low — the Pyodide path is currently broken (refresh never completes), so no working behavior depends on the current blocking call; the non-Pyodide path is unchanged by construction.
