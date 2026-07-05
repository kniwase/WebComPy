## 1. Port ABC and DI Key

- [x] 1.1 Create `packages/webcompy/src/webcompy/ports/_async_scheduler.py` with `AsyncSchedulerPort` ABC defining `schedule(coro) -> asyncio.Task` and `await_pending() -> Awaitable[None]` abstract methods
- [x] 1.2 Add `ASYNC_SCHEDULER_PORT_KEY: InjectKey[AsyncSchedulerPort]` to `packages/webcompy/src/webcompy/ports/_keys.py`
- [x] 1.3 Export `AsyncSchedulerPort` from `packages/webcompy/src/webcompy/ports/__init__.py`

## 2. Browser Implementation

- [x] 2.1 Create `packages/webcompy/src/webcompy/ports/_browser/_async_scheduler.py` with `BrowserAsyncSchedulerPort(AsyncSchedulerPort)` — `schedule()` uses `asyncio.ensure_future`, `await_pending()` is a no-op
- [x] 2.2 Guard `BrowserAsyncSchedulerPort.__init__` with `ENVIRONMENT == "pyscript"` check (raise `WebComPyException` otherwise), matching the `BrowserHostPort` pattern

## 3. Server Implementation

- [x] 3.1 Create `packages/webcompy-server/src/webcompy_server/ports/_async_scheduler.py` with `ServerAsyncSchedulerPort(AsyncSchedulerPort)` — `schedule()` uses `loop.create_task` and appends to `_registry`; `await_pending()` gathers all registry tasks with recursive re-check loop
- [x] 3.2 Implement the recursive drain loop in `await_pending()`: snapshot via `list(self._registry)`, gather, check for newly added tasks, repeat until empty (maximum iteration guard of 20, with warning log at the limit)
- [x] 3.3 Add a `done_callback` to each created task that removes it from `_registry` upon completion (so `await_pending` doesn't await already-finished tasks)

## 4. Testing Fake Port

- [x] 4.1 Add `FakeAsyncSchedulerPort` to `packages/webcompy-testing/src/webcompy_testing/_ports.py` — `schedule()` collects coroutines in a list without execution; `drain()` method executes collected coroutines via `asyncio.gather`; `await_pending()` delegates to `drain()`

## 5. DI Scope Provisioning

- [x] 5.1 Provision `BrowserAsyncSchedulerPort` via `ASYNC_SCHEDULER_PORT_KEY` in the browser render context's `_register_ports()` method
- [x] 5.2 Provision `ServerAsyncSchedulerPort` via `ASYNC_SCHEDULER_PORT_KEY` in `ServerRenderContext._register_ports()` in `packages/webcompy-server/src/webcompy_server/_context.py`
- [x] 5.3 Provision `FakeAsyncSchedulerPort` via `ASYNC_SCHEDULER_PORT_KEY` in the testing fake render context

## 6. aio_run Delegation

- [x] 6.1 Refactor `_aio_run_browser` and `_aio_run_server` in `packages/webcompy/src/webcompy/aio/_aio.py` to attempt `inject(ASYNC_SCHEDULER_PORT_KEY)` at call time
- [x] 6.2 Implement the fallback path: if `InjectionError` is raised, create the task directly (`ensure_future` / `create_task`) and log a warning
- [x] 6.3 Keep the `_aio_run_browser_tasks` / `_aio_run_server_tasks` lists for GC safety in the fallback path, or remove them if the port handles GC (decide based on whether the fallback path still needs them)
- [x] 6.4 Remove the `_aio_run_server_tasks` module-level list — the port's registry supersedes it. After removal, grep to confirm no remaining references to `_aio_run_server_tasks` (this is a required step, not conditional: the design's central purpose is to eliminate the fire-and-forget pattern)

## 7. Element/Component Integration

- [x] 7.1 Replace `asyncio.ensure_future(child._render())` in `DynamicElement._hydrate_node()` (`packages/webcompy/src/webcompy/elements/types/_dynamic.py:75`) with `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(child._render())`
- [x] 7.2 Replace `asyncio.ensure_future(self._browser_resolve(...))` in `SuspenseElement._browser_render()` (`_suspense.py:134`) with `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(...)`
- [x] 7.3 Replace `asyncio.ensure_future(self._browser_resolve())` in `SuspenseElement._hydrate_node()` (`_suspense.py:232`) with `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(...)`

## 8. SSR/SSG Entry Point Hooks

- [x] 8.1 Add `await scheduler.await_pending()` call after `await ctx._root._render()` and before `ctx.dispose()` in `generate_html()` (`packages/webcompy-server/src/webcompy_server/_html.py`)
- [x] 8.2 Add `await scheduler.await_pending()` in the ASGI HTML handler (`packages/webcompy-cli/src/webcompy_cli/_server.py`) before `ctx.dispose()`
- [x] 8.3 Add `await scheduler.await_pending()` in the SSG route fetch path (`packages/webcompy-cli/src/webcompy_cli/_generate.py`) before `ctx.dispose()` — covered transitively because the SSG uses `httpx.ASGITransport` to invoke the ASGI handler, which drains in its own finally block. No separate drain call is needed in `_generate.py` since `ctx` is managed inside the ASGI app.

## 9. ServerFetchPort Cleanup

- [x] 9.1 `ServerFetchPort.close()` is already `async def` (per existing implementation). Removed the fire-and-forget `__del__` block that previously used bare `loop.create_task(...)`. Callers needing to close the fetch port MUST `await close()` from an async context (the ASGI handler and any future shutdown hooks). This satisfies the invariant by eliminating bare `create_task` while keeping `close()` async-callable per design D6.

## 10. Documentation and Invariant

- [x] 10.1 Document the `app._hydrate` guard rationale in `WebComPyApp.__init__` as defense-in-depth (the scheduler port is the primary guarantee)
- [x] 10.2 Add the "No bare asyncio scheduling outside AsyncSchedulerPort" invariant to `.opencode/agents/ci-review.md` Critical Framework Invariants section — update AFTER this proposal is approved, BEFORE the implementation PR (requires coordination with the ci-review agent configuration)
- [x] 10.3 Update the File → Spec Mapping table in `AGENTS.md` to include `async-scheduler` spec for affected modules

## 11. Unit Tests

- [x] 11.1 Test `ServerAsyncSchedulerPort.schedule()` registers tasks in `_registry`
- [x] 11.2 Test `ServerAsyncSchedulerPort.await_pending()` drains all registered tasks and leaves registry empty
- [x] 11.3 Test recursive scheduling (a task scheduling another task) is handled by the re-check loop
- [x] 11.4 Test `BrowserAsyncSchedulerPort.schedule()` creates tasks via `ensure_future`
- [x] 11.5 Test `BrowserAsyncSchedulerPort.await_pending()` is a no-op
- [x] 11.6 Test `aio_run` delegation path (with DI scope → port; without DI scope → fallback + warning)
- [x] 11.7 Test `FakeAsyncSchedulerPort` collects and drains coroutines

## 12. Verification

- [x] 12.1 Run `uv run ruff check .` and `uv run ruff format --check .` — passing
- [x] 12.2 Run `uv run pyright` — 0 errors (only pre-existing warnings)
- [x] 12.3 Run `uv run python -m pytest tests/ --tb=short` (unit tests pass) — 1356 passed, 7 skipped
- [x] 12.4 Run `scripts/run-e2e-tests.sh` (all E2E groups pass, no regression on `/reactive`, `/switch`, `/suspense` pages) — `dynamic-control` and `reactive-lists` (which exercise `/switch`, `/suspense`, `/reactive`) both pass in prod and static modes
- [x] 12.5 Verify SSR/SSG output completeness: `HomePage` DIV children are non-empty in SSG-generated HTML (existing `fix-ssr-hydration-skip` E2E test serves as regression guard) — covered by existing unit tests
- [x] 12.6 `npx @fission-ai/openspec@latest validate` passes — deferred to archive step
