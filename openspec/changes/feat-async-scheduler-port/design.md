# Design: Async Scheduler Port

## Context

WebComPy operates in two runtime environments with fundamentally different event-loop lifecycles:

- **Browser (PyScript/Emscripten)**: The event loop runs for the entire page lifetime. Fire-and-forget tasks (`asyncio.ensure_future`) complete eventually because the loop never exits during normal operation.
- **Server (CPython)**: Each SSR/SSG render is a single-shot async operation. `await generate_html()` drives the render tree to completion, then `ctx.dispose()` tears down the DI scope. Any task scheduled via fire-and-forget may execute *after* disposal, accessing a torn-down DI scope and raising `InjectKey` resolution errors.

The `fix-ssr-hydration-skip` change patched one manifestation (`DynamicElement._hydrate_node` scheduling `ensure_future(child._render())` that ran post-dispose). But five fire-and-forget scheduling sites remain:

| Site | File | Current mechanism |
|------|------|-------------------|
| Root render + async callbacks | `aio/_aio.py` | `ensure_future` (browser) / `create_task` (server, never awaited) |
| Hydrate unmounted children | `elements/types/_dynamic.py:75` | `ensure_future` |
| Suspense browser resolve | `elements/types/_suspense.py:134` | `ensure_future` |
| Suspense hydrate resolve | `elements/types/_suspense.py:232` | `ensure_future` |
| FetchPort cleanup | `server/ports/_fetch.py` | `create_task` (`# noqa: RUF006`) |

The server-side `_aio_run_server_tasks` list is appended to but **never gathered** — orphaned tasks accumulate without completion guarantees.

## Goals / Non-Goals

**Goals:**

- Centralize all async task scheduling behind a single typed, injectable port (`AsyncSchedulerPort`).
- Guarantee that on the server, all scheduled tasks complete before `ctx.dispose()` runs, via a registry-and-drain pattern.
- Eliminate the class of dual-environment lifecycle bugs (not just the `_hydrate_node` instance).
- Preserve exact browser behavior (fire-and-forget on a long-lived loop remains correct).
- Provide a testing-friendly fake port for browserless unit tests.

**Non-Goals:**

- Removing the `app._hydrate` environment guard (retained as defense-in-depth).
- Making `_hydrate_node()` async (caused E2E regressions per `async-rendering` spec).
- Parallel sibling rendering via `asyncio.gather` (separate future work).
- Changing `HostPort.schedule_macro_task()` (already environment-aware; remains separate).
- Adding retry/backoff/cancellation policies to scheduled tasks.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                   AsyncSchedulerPort (ABC)                    │
│   schedule(coro: Coroutine) -> asyncio.Task                   │
│   await_pending() -> Awaitable[None]                          │
└────────────────────────┬─────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
┌──────────────────────┐  ┌──────────────────────────────────┐
│ BrowserAsyncScheduler│  │ ServerAsyncScheduler             │
│                      │  │                                  │
│ schedule:            │  │ schedule:                        │
│   ensure_future(coro)│  │   task = create_task(coro)       │
│   (fire-and-forget)  │  │   _registry.append(task)         │
│                      │  │                                  │
│ await_pending:       │  │ await_pending:                   │
│   no-op (long-lived  │  │   done, pending = partition(...) │
│   loop persists)     │  │   await gather(*pending)         │
│                      │  │   (drains before ctx.dispose())  │
└──────────────────────┘  └──────────────────────────────────┘
```

### Registry-and-Drain Flow (Server)

```
  generate_html() / ASGI handler
      │
      ▼
  ctx = app.create_render_context(path)
      │  (DI scope provides ServerAsyncSchedulerPort instance)
      ▼
  await ctx._root._render()
      │  ├── Component._render() → may call aio_run(callback)
      │  │     └── scheduler.schedule(callback_coro) → registered
      │  ├── SuspenseElement._render() → scheduler.schedule(resolve)
      │  │     └── registered
      │  └── DynamicElement._hydrate_node() [browser-only path,
      │        but if reached, scheduler.schedule(render)]
      │
      ▼
  await scheduler.await_pending()    ← NEW: drain all registered tasks
      │  (gather completes all pending coroutines)
      ▼
  ctx.dispose()                       ← safe: no orphaned tasks
```

## Decisions

### D1: Single port for all async scheduling (broad scope)

All five fire-and-forget sites route through `AsyncSchedulerPort`. This includes `aio_run` (the general-purpose resolver used by `resolve_async`, `AsyncWrapper`, and the root browser render).

**Alternatives considered:**
- **Narrow scope** (only the 4 render-task sites, leave `aio_run` as-is): Smaller change, but `_aio_run_server_tasks` remains a latent fire-and-forget. Any future code calling `resolve_async` during SSR would reintroduce the bug. Rejected — does not generalize the fix.
- **Two ports** (`RenderSchedulerPort` for render tasks, `AsyncRunnerPort` for `aio_run`): Conceptually cleaner separation, but doubles the surface area and the server implementations would be nearly identical. Rejected — unnecessary complexity.

**Rationale:** A single chokepoint makes the invariant "no bare `ensure_future`/`create_task` outside the port" enforceable and meaningful. The naming `AsyncSchedulerPort` (rather than `RenderSchedulerPort`) reflects the broader scope.

### D2: Registry ownership — per-context, not module-global

The `ServerAsyncSchedulerPort` instance is created per `RenderContext` and provisioned in the context's DI scope. Its internal `_registry: list[asyncio.Task]` is therefore per-request, not shared across concurrent SSR requests.

**Concurrent modification guard:** Task `done_callback`s remove completed tasks from `_registry`. If a callback fires while `await_pending()` is iterating `_registry`, the list mutates during iteration, risking `RuntimeError: list changed size during iteration` or missed tasks. The implementation SHALL snapshot the registry before iteration:

```python
async def await_pending(self):
    iteration = 0
    while self._registry:
        tasks = list(self._registry)  # snapshot — callbacks may mutate _registry concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        iteration += 1
        if iteration > 20:
            logging.warning("await_pending exceeded 20 drain iterations; "
                            "possible recursive scheduling bug")
            break
```

The `list(self._registry)` snapshot copies references at iteration start; concurrent `done_callback` removals affect the live list, not the snapshot. The snapshot approach is preferred over locking because `done_callback`s run synchronously on the event loop (not from another thread), and `await` points yield control — so a `deque` with locks would add complexity without benefit in the single-threaded asyncio model.

**Alternatives considered:**
- **Module-global registry** (single list shared across all requests): Simpler, but concurrent SSR requests would interleave tasks, and `await_pending()` for one request would await another request's tasks. Rejected — breaks request isolation.
- **`collections.deque` with locks**: Over-engineered for single-threaded asyncio. The snapshot approach is simpler and sufficient.

**Rationale:** The port owns its registry. Per-instance = per-request. The DI scope provides isolation naturally.

### D3: `aio_run` delegation with fallback

`aio_run` (selected at module load: `_aio_run_browser` or `_aio_run_server`) is refactored to attempt `inject(ASYNC_SCHEDULER_PORT_KEY)` at call time. If the injection succeeds (a DI scope is active), the task is scheduled via the port. If injection fails (called outside a render context, e.g., in CLI utilities or module-level code), the fallback creates the task directly and logs a warning.

```
  aio_run(coro):
      try:
          scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
      except InjectionError:
          # Fallback: no DI scope active
          logging.warning("aio_run called outside render context; "
                          "task may not be awaited on server")
          task = ensure_future(coro)  # browser
                  # or create_task(coro)  # server
      else:
          task = scheduler.schedule(coro)
      _track_task(task)  # keep reference for GC safety
```

**Rationale:** `aio_run` is called from diverse contexts — some within render (component lifecycle hooks, Suspense resolution) and some outside (CLI bootstrap, testing utilities). The fallback preserves backward compatibility while the render-context path gets full registry-drain guarantees.

### D4: `await_pending()` called by entry points, not by the port itself

The port does not auto-drain. The SSR/SSG entry points explicitly call `await scheduler.await_pending()` after the render tree completes and before `ctx.dispose()`. This makes the drain timing explicit and auditable.

**Call sites:**
- `generate_html()` in `webcompy_server/_html.py`
- ASGI HTML handler in `webcompy_cli/_server.py`
- SSG route fetch loop in `webcompy_cli/_generate.py`

**Rationale:** Auto-draining (e.g., in a `__del__` or context-manager exit) would hide the timing and make debugging harder. Explicit calls are self-documenting.

### D5: Browser `await_pending()` is a no-op

On the browser, the event loop is long-lived. Tasks scheduled via `ensure_future` complete naturally. `await_pending()` returns immediately (empty coroutine). This keeps the call sites symmetric across environments without imposing browser-side waiting.

### D6: `ServerFetchPort.close()` cleanup tasks

`ServerFetchPort.close()` currently uses `loop.create_task(self._external_client.aclose())` with `# noqa: RUF006`. Two options:

- **Route through scheduler**: `scheduler.schedule(self._external_client.aclose())`. The task is registered and drained. But `close()` is typically called during teardown *after* `await_pending()`, so the registry drain may not cover it.
- **Make `close()` async and await explicitly**: `await self._external_client.aclose()`. The caller (`ctx.dispose()` or the port's own teardown) awaits `close()`.

**Decision:** Make `close()` async (or add an `aclose()` async variant) and have `ctx.dispose()` await it. This is more correct than relying on the scheduler for teardown-order cleanup. The scheduler handles *render-time* tasks; teardown cleanup is a separate lifecycle concern.

### D7: Fake port for testing

`FakeAsyncSchedulerPort` (in `webcompy_testing`) collects scheduled coroutines in a list. Tests can either:
- Call `await fake_scheduler.drain()` to run all collected coroutines, or
- Inspect the list to assert what was scheduled.

This matches the existing fake-port pattern in `webcompy_testing/_ports.py`.

## Risks / Trade-offs

- **[Orphaned tasks if `await_pending()` is forgotten]** → Mitigation: Document the invariant in `app-lifecycle` spec that all SSR/SSG entry points MUST call `await_pending()` before `dispose()`. The `ci-review` agent enforces this invariant.

- **[Fallback path masks missing DI scope]** → Mitigation: The fallback logs a warning. In development, the warning surfaces misconfigured code. In production, the fallback still creates the task (preserving behavior); it just lacks the drain guarantee.

- **[Performance overhead of registry bookkeeping]** → Mitigation: The registry is a simple list append/remove. `await_pending()` gathers only the remaining tasks. For typical renders with 0-5 scheduled tasks, overhead is negligible.

- **[Deadlock if a scheduled task schedules another task]** → Mitigation: `await_pending()` should handle this by re-checking for newly added tasks after the initial gather. Implementation: loop until the registry is empty (with a maximum iteration guard of 20 and a warning log at the limit to surface genuine recursive-scheduling bugs early).

- **[Browser behavior change]** → Mitigation: `BrowserAsyncSchedulerPort.schedule()` wraps the exact same `ensure_future` call. No behavioral change on browser. Existing E2E tests (`/reactive`, `/switch`, `/suspense` pages) verify no regression.

## Open Questions

1. **Should `await_pending()` have a timeout?** If a scheduled task hangs, `await_pending()` blocks forever. A configurable timeout (defaulting to the Suspense timeout of 10s, or a separate value) would prevent indefinite hangs. Deferred to implementation — a reasonable default can be chosen during coding.

2. **Should the registry track task exceptions?** Currently, `ensure_future` tasks with exceptions log via `add_done_callback`. The port could centralize exception handling, but this overlaps with `resolve_async`'s `on_error` hook. Decision: keep exception handling at the call site; the port is a scheduling mechanism, not an error boundary.

3. **Interaction with nested DI scopes (Suspense)**: `SuspenseElement._render()` provides `SUSPENSE_RESOLVING_KEY` in a child scope. Tasks scheduled within that scope use the same scheduler instance (DI traversal finds the nearest provision, which is the context-level scheduler). No issue expected, but needs verification during implementation.
