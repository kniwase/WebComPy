# Proposal: Async Scheduler Port

## Why

WebComPy's dual-environment architecture (browser via PyScript with a long-lived event loop, server via CPython with single-shot renders) creates an asymmetry in how asynchronous tasks should be scheduled. On the browser, fire-and-forget scheduling (`asyncio.ensure_future`) is correct because the event loop persists indefinitely. On the server, fire-and-forget tasks may execute after `ctx.dispose()` runs and the DI scope is torn down, causing `InjectKey` resolution failures and incomplete SSR/SSG output.

This problem manifested concretely in `fix-ssr-hydration-skip` (#189 prerequisite), where `DynamicElement._hydrate_node()` scheduled `asyncio.ensure_future(child._render())` tasks that ran after the server render's await chain returned. The fix applied a minimal workaround (`app._hydrate = config.hydrate and ENVIRONMENT == "pyscript"`), but the root cause — scattered `asyncio.ensure_future` / `loop.create_task` calls with no environment-aware scheduling — remains. There are currently **five** fire-and-forget scheduling sites across the codebase (`_aio.py`, `_dynamic.py`, two in `_suspense.py`, `ServerFetchPort.close`), each a latent source of the same dual-environment lifecycle bug.

This change introduces an `AsyncSchedulerPort` that becomes the single chokepoint for all async task scheduling. The server implementation registers tasks in a per-request registry and provides an `await_pending()` method that the SSR/SSG entry points call before `ctx.dispose()`, structurally guaranteeing that no orphaned tasks outlive the render context. This generalizes the fix beyond the specific `_hydrate_node` instance to the entire class of dual-environment scheduling bugs.

## What Changes

- **NEW** `AsyncSchedulerPort` ABC in `packages/webcompy/src/webcompy/ports/_async_scheduler.py` — Defines `schedule(coro: Coroutine) -> asyncio.Task` and `await_pending() -> Awaitable[None]` as the unified async scheduling interface.
- **NEW** `BrowserAsyncSchedulerPort` in `packages/webcompy/src/webcompy/ports/_browser/_async_scheduler.py` — Wraps `asyncio.ensure_future` (fire-and-forget). `await_pending()` is a no-op because the browser event loop is long-lived.
- **NEW** `ServerAsyncSchedulerPort` in `packages/webcompy-server/src/webcompy_server/ports/_async_scheduler.py` — Creates tasks via `loop.create_task` and registers them in an internal registry. `await_pending()` gathers all registered tasks, ensuring completion before the render context is disposed.
- **NEW** `ASYNC_SCHEDULER_PORT_KEY: InjectKey[AsyncSchedulerPort]` in `packages/webcompy/src/webcompy/ports/_keys.py`.
- **MODIFIED** `packages/webcompy/src/webcompy/aio/_aio.py` — `_aio_run_browser` and `_aio_run_server` delegate to `AsyncSchedulerPort.schedule()` when a DI scope is active, with a fallback to direct task creation (plus a warning log) when called outside a render context.
- **MODIFIED** `packages/webcompy/src/webcompy/elements/types/_dynamic.py` — `DynamicElement._hydrate_node()` calls `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(child._render())` instead of `asyncio.ensure_future`.
- **MODIFIED** `packages/webcompy/src/webcompy/elements/types/_suspense.py` — Both `ensure_future` call sites (`_browser_render` and `_hydrate_node`) route through `AsyncSchedulerPort.schedule()`.
- **MODIFIED** `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` — `ServerFetchPort.close()` schedules cleanup tasks through the port (or awaits them explicitly) instead of bare `loop.create_task`.
- **MODIFIED** `packages/webcompy/src/webcompy/app/_app.py` — The `app._hydrate` workaround is retained but its rationale is documented as "the scheduler port makes hydration scheduling safe; the environment guard is a defense-in-depth measure."
- **MODIFIED** SSR/SSG entry points (`packages/webcompy-server/src/webcompy_server/_html.py`, `packages/webcompy-cli/src/webcompy_cli/_server.py`, `packages/webcompy-cli/src/webcompy_cli/_generate.py`) — Call `await scheduler.await_pending()` after the render tree completes and before `ctx.dispose()`.
- **MODIFIED** `packages/webcompy-testing/src/webcompy_testing/_ports.py` — Add a `FakeAsyncSchedulerPort` for browserless testing that runs tasks synchronously or collects them for explicit awaiting.

## Capabilities

### New Capabilities

- `async-scheduler`: A typed, injectable port that centralizes all async task scheduling. The server implementation maintains a per-request task registry drained before context disposal, structurally preventing dual-environment lifecycle bugs.

### Modified Capabilities

- `port-abstraction`: A new `AsyncSchedulerPort` ABC joins the existing port hierarchy alongside `DOMPort`, `FetchPort`, `HostPort`, etc.
- `port-provisioning`: `ASYNC_SCHEDULER_PORT_KEY` is provisioned in both browser and server DI scopes during context initialization.
- `async-rendering`: `_hydrate_node()` and Suspense's browser resolution schedule tasks via `AsyncSchedulerPort` instead of direct `asyncio.ensure_future`.
- `app-lifecycle`: SSR/SSG entry points (`generate_html`, ASGI HTML handler, SSG route fetch) SHALL call `await_pending()` before `ctx.dispose()` to guarantee all scheduled tasks complete.
- `elements`: `DynamicElement._hydrate_node()` and `SuspenseElement` use the scheduler port for async task creation.

## Known Issues Addressed

- **Dual-environment lifecycle bug (generalized)** — `fix-ssr-hydration-skip` patched the specific `_hydrate_node` manifestation. This change addresses the root cause: all fire-and-forget scheduling sites are routed through a port whose server implementation guarantees task completion before context disposal. The bug class is structurally eliminated (modulo the convention that no new bare `asyncio.ensure_future` / `loop.create_task` calls are added outside the port — enforced as a framework invariant).
- **`_aio_run_server_tasks` never awaited** — `_aio_run_server` appends tasks to a module-level list that is never gathered. Tasks created via `resolve_async` / `AsyncWrapper` during server renders were orphaned. The scheduler port's registry-and-drain pattern resolves this.

## Non-goals

- **Removing the `app._hydrate` environment guard** — The `app._hydrate = config.hydrate and ENVIRONMENT == "pyscript"` line stays as a defense-in-depth measure. A future change may remove it once the scheduler port is battle-tested.
- **Changing `_hydrate_node()` to be `async def`** — `_hydrate_node()` remains synchronous. The async render pipeline spec (`async-rendering`) documents that making `_hydrate_node` async caused E2E regressions. The scheduler port does not require this change.
- **Changing the signal system or reactive contracts** — This change only affects task scheduling, not signal graph semantics.
- **Parallel sibling rendering** — `asyncio.gather` for sibling children is tracked as separate future work. Sequential sibling rendering is preserved.
- **Changing the `schedule_macro_task` API on `HostPort`** — `schedule_macro_task` is already environment-aware (server: synchronous, browser: `setTimeout`). It remains separate from `AsyncSchedulerPort`, which handles coroutine scheduling specifically.
- **Adding retry or backoff semantics to task scheduling** — The port schedules tasks as-is; error handling remains the caller's responsibility.

## Impact

- **Affected modules**:
  - `packages/webcompy/src/webcompy/ports/` (new ABC + browser impl + DI key)
  - `packages/webcompy-server/src/webcompy_server/ports/` (new server impl)
  - `packages/webcompy/src/webcompy/aio/` (`aio_run` delegation)
  - `packages/webcompy/src/webcompy/elements/types/` (`_dynamic.py`, `_suspense.py`)
  - `packages/webcompy/src/webcompy/app/` (`_app.py` documentation)
  - `packages/webcompy-server/src/webcompy_server/` (`_html.py`, `_context.py` — `await_pending` hook)
  - `packages/webcompy-cli/src/webcompy_cli/` (`_server.py`, `_generate.py` — `await_pending` call)
  - `packages/webcompy-testing/src/webcompy_testing/` (fake port)
- **Breaking**: None for public APIs. `aio_run` remains callable but internally delegates to the port when available. The `_aio_run_server_tasks` module-level list is superseded by the port's registry (the list is removed or kept only as the fallback path).
- **Backward compatible**: All existing user code works unchanged. The port is an internal infrastructure improvement.
- **Testing**: Unit tests for the registry-drain mechanism, the fallback path when no DI scope is active, and the `await_pending` timing relative to `ctx.dispose()`. E2E tests verify SSR/SSG output completeness (the existing `fix-ssr-hydration-skip` E2E test serves as a regression guard).
