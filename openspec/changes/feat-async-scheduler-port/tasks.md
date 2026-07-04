## 1. Port ABC and DI Key

- [ ] 1.1 Create `packages/webcompy/src/webcompy/ports/_async_scheduler.py` with `AsyncSchedulerPort` ABC defining `schedule(coro) -> asyncio.Task` and `await_pending() -> Awaitable[None]` abstract methods
- [ ] 1.2 Add `ASYNC_SCHEDULER_PORT_KEY: InjectKey[AsyncSchedulerPort]` to `packages/webcompy/src/webcompy/ports/_keys.py`
- [ ] 1.3 Export `AsyncSchedulerPort` from `packages/webcompy/src/webcompy/ports/__init__.py`

## 2. Browser Implementation

- [ ] 2.1 Create `packages/webcompy/src/webcompy/ports/_browser/_async_scheduler.py` with `BrowserAsyncSchedulerPort(AsyncSchedulerPort)` — `schedule()` uses `asyncio.ensure_future`, `await_pending()` is a no-op
- [ ] 2.2 Guard `BrowserAsyncSchedulerPort.__init__` with `ENVIRONMENT == "pyscript"` check (raise `WebComPyException` otherwise), matching the `BrowserHostPort` pattern

## 3. Server Implementation

- [ ] 3.1 Create `packages/webcompy-server/src/webcompy_server/ports/_async_scheduler.py` with `ServerAsyncSchedulerPort(AsyncSchedulerPort)` — `schedule()` uses `loop.create_task` and appends to `_registry`; `await_pending()` gathers all registry tasks with recursive re-check loop
- [ ] 3.2 Implement the recursive drain loop in `await_pending()`: gather, check for newly added tasks, repeat until empty (with a maximum iteration guard, e.g., 100, to prevent infinite loops from buggy recursive scheduling)
- [ ] 3.3 Add a `done_callback` to each created task that removes it from `_registry` upon completion (so `await_pending` doesn't await already-finished tasks)

## 4. Testing Fake Port

- [ ] 4.1 Add `FakeAsyncSchedulerPort` to `packages/webcompy-testing/src/webcompy_testing/_ports.py` — `schedule()` collects coroutines in a list without execution; `drain()` method executes collected coroutines via `asyncio.gather`; `await_pending()` delegates to `drain()`

## 5. DI Scope Provisioning

- [ ] 5.1 Provision `BrowserAsyncSchedulerPort` via `ASYNC_SCHEDULER_PORT_KEY` in the browser render context's `_register_ports()` method
- [ ] 5.2 Provision `ServerAsyncSchedulerPort` via `ASYNC_SCHEDULER_PORT_KEY` in `ServerRenderContext._register_ports()` in `packages/webcompy-server/src/webcompy_server/_context.py`
- [ ] 5.3 Provision `FakeAsyncSchedulerPort` via `ASYNC_SCHEDULER_PORT_KEY` in the testing fake render context

## 6. aio_run Delegation

- [ ] 6.1 Refactor `_aio_run_browser` and `_aio_run_server` in `packages/webcompy/src/webcompy/aio/_aio.py` to attempt `inject(ASYNC_SCHEDULER_PORT_KEY)` at call time
- [ ] 6.2 Implement the fallback path: if `InjectionError` is raised, create the task directly (`ensure_future` / `create_task`) and log a warning
- [ ] 6.3 Keep the `_aio_run_browser_tasks` / `_aio_run_server_tasks` lists for GC safety in the fallback path, or remove them if the port handles GC (decide based on whether the fallback path still needs them)
- [ ] 6.4 Remove the now-unused `_aio_run_server_tasks` list if the port's registry supersedes it (verify no other code references it)

## 7. Element/Component Integration

- [ ] 7.1 Replace `asyncio.ensure_future(child._render())` in `DynamicElement._hydrate_node()` (`packages/webcompy/src/webcompy/elements/types/_dynamic.py:75`) with `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(child._render())`
- [ ] 7.2 Replace `asyncio.ensure_future(self._browser_resolve(...))` in `SuspenseElement._browser_render()` (`_suspense.py:134`) with `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(...)`
- [ ] 7.3 Replace `asyncio.ensure_future(self._browser_resolve())` in `SuspenseElement._hydrate_node()` (`_suspense.py:232`) with `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(...)`

## 8. SSR/SSG Entry Point Hooks

- [ ] 8.1 Add `await scheduler.await_pending()` call after `await ctx._root._render()` and before `ctx.dispose()` in `generate_html()` (`packages/webcompy-server/src/webcompy_server/_html.py`)
- [ ] 8.2 Add `await scheduler.await_pending()` in the ASGI HTML handler (`packages/webcompy-cli/src/webcompy_cli/_server.py`) before `ctx.dispose()`
- [ ] 8.3 Add `await scheduler.await_pending()` in the SSG route fetch path (`packages/webcompy-cli/src/webcompy_cli/_generate.py`) before `ctx.dispose()`

## 9. ServerFetchPort Cleanup

- [ ] 9.1 Refactor `ServerFetchPort.close()` to make cleanup tasks awaitable — either route through `AsyncSchedulerPort` or make `close()` / add `aclose()` async and have `ctx.dispose()` await it explicitly

## 10. Documentation and Invariant

- [ ] 10.1 Document the `app._hydrate` guard rationale in `WebComPyApp.__init__` as defense-in-depth (the scheduler port is the primary guarantee)
- [ ] 10.2 Add the "No bare asyncio scheduling outside AsyncSchedulerPort" invariant to `.opencode/agents/ci-review.md` Critical Framework Invariants section
- [ ] 10.3 Update the File → Spec Mapping table in `AGENTS.md` to include `async-scheduler` spec for affected modules

## 11. Unit Tests

- [ ] 11.1 Test `ServerAsyncSchedulerPort.schedule()` registers tasks in `_registry`
- [ ] 11.2 Test `ServerAsyncSchedulerPort.await_pending()` drains all registered tasks and leaves registry empty
- [ ] 11.3 Test recursive scheduling (a task scheduling another task) is handled by the re-check loop
- [ ] 11.4 Test `BrowserAsyncSchedulerPort.schedule()` creates tasks via `ensure_future`
- [ ] 11.5 Test `BrowserAsyncSchedulerPort.await_pending()` is a no-op
- [ ] 11.6 Test `aio_run` delegation path (with DI scope → port; without DI scope → fallback + warning)
- [ ] 11.7 Test `FakeAsyncSchedulerPort` collects and drains coroutines

## 12. Verification

- [ ] 12.1 Run `uv run ruff check .` and `uv run ruff format --check .`
- [ ] 12.2 Run `uv run pyright`
- [ ] 12.3 Run `uv run python -m pytest tests/ --tb=short` (unit tests pass)
- [ ] 12.4 Run `scripts/run-e2e-tests.sh` (all E2E groups pass, no regression on `/reactive`, `/switch`, `/suspense` pages)
- [ ] 12.5 Verify SSR/SSG output completeness: `HomePage` DIV children are non-empty in SSG-generated HTML (existing `fix-ssr-hydration-skip` E2E test serves as regression guard)
- [ ] 12.6 `npx @fission-ai/openspec@latest validate` passes
