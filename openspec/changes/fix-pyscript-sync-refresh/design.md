# Design: fix-pyscript-sync-refresh

## Context

Dynamic containers dispatch signal-driven refreshes through `_run_refresh_sync` (`packages/webcompy/src/webcompy/elements/types/_dynamic.py:32-46`):

```python
def _run_refresh_sync(refresh, *args):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(refresh(*args))
    else:
        if ENVIRONMENT != "pyscript":
            # nest_asyncio patch ...
        loop.run_until_complete(refresh(*args))
```

In Pyodide, a DOM event handler (e.g., `@click` → `del data[k]` → signal notify → `_refresh_sync`) runs as a **synchronous** JS→Python entrypoint. Pyodide's webloop only allows `run_until_complete` (stack switching) from an entrypoint invoked via `callPromising`; from a synchronous entrypoint it raises:

```
RuntimeError: Cannot stack switch because the Python entrypoint was a synchronous function.
```

Empirically (docs todo demo, Playwright-instrumented): the refresh coroutine's synchronous prefix runs (up to the first `await`), then the exception propagates — the async remainder of the refresh is dropped and a `pageerror` is logged. The DOM ends up half-updated; the outcome depends on which operations happened to be in the sync prefix.

The codebase already has a working async-scheduling pattern for exactly this environment: `_resolve_async_callback` (`packages/webcompy/src/webcompy/aio/_aio.py:118-133`) schedules async signal callbacks via `aio_run(_safe())` in the Pyodide environment and blocks via `asyncio.run`/`nest_asyncio` elsewhere. `aio_run` (`_aio.py:38-60`) resolves to a browser implementation that schedules on `ASYNC_SCHEDULER_PORT` (falling back to `asyncio.ensure_future`) and returns immediately.

## Goals / Non-Goals

**Goals:**

- In the Pyodide environment, signal-driven refreshes dispatched from synchronous DOM event handlers complete fully (scheduled on the event loop) without raising "Cannot stack switch" and without logging a pageerror.
- Non-Pyodide environments keep the current synchronous-blocking semantics exactly, so unit tests and `TestRenderer` immediate assertions remain valid.
- Minimal, single-point change (`_run_refresh_sync`), reusing the existing `aio_run` mechanism.

**Non-Goals:**

- Coalescing/deduplication of queued refreshes (each mutation schedules one refresh; each reconciles from the current signal value — last-state-wins is acceptable).
- Changing `DynamicElement._render` / `_hydrate_node` or the refresh bodies.
- Making non-Pyodide refresh asynchronous.

## Decisions

### D1: In Pyodide, schedule the refresh on the event loop via `aio_run` instead of `loop.run_until_complete`

`_run_refresh_sync` gains a Pyodide branch:

```python
def _run_refresh_sync(refresh, *args):
    from webcompy.utils._environment import ENVIRONMENT

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(refresh(*args))
    else:
        if ENVIRONMENT == "pyscript":
            from webcompy import logging
            from webcompy.aio._aio import aio_run

            async def _safe_refresh() -> None:
                try:
                    await refresh(*args)
                except Exception as err:
                    logging.error(err)

            aio_run(_safe_refresh())
        else:
            import nest_asyncio
            # ... existing nest_asyncio patch ...
            loop.run_until_complete(refresh(*args))
```

Rationale:

- `aio_run` is the established mechanism for fire-and-forget coroutine scheduling in the browser (`_resolve_async_callback` uses it for async signal callbacks), so this keeps refresh dispatch consistent with the rest of the framework.
- The `_safe_refresh` wrapper converts refresh exceptions into `logging.error` — previously the exception surfaced as a pageerror; now it is logged without corrupting the event handler, and refresh failures remain observable in console logs.
- The branch is keyed on `ENVIRONMENT == "pyscript"` (the same condition the existing code already checks for the `nest_asyncio` skip), so non-Pyodide behavior is byte-for-byte unchanged.

*Alternatives considered*:

- **(a) Register the async `_refresh` callback unconditionally in Pyodide** (`callback = self._refresh if (has_async or ENVIRONMENT == "pyscript") else self._refresh_sync`): routes through `_resolve_async_callback`, which already handles Pyodide scheduling. Rejected: touches three registration sites (`RepeatElement._render`, `SwitchElement._render`, `MarkdownForElement._render`), couples the callback-choice logic to the environment, and leaves `_run_refresh_sync` broken for any other caller.
- **(b) Wrap event-handler proxies so Pyodide invokes them via `callPromising`**: would make stack switching available for the whole handler. Rejected: changes invocation semantics for every DOM event handler (timing, return values), far broader blast radius than the refresh path.
- **(c) Formalize partial execution** (run only the sync prefix and swallow the error): codifies the current broken behavior. Rejected: refresh never completes, DOM stays half-updated, and failures become invisible.

## Risks / Trade-offs

- [Refresh becomes asynchronous in the browser] → DOM updates after a mutation land on the next event-loop iteration. E2E tests use Playwright locator auto-waiting, so existing assertions remain valid; verified by the full e2e suite. The docs todo `test_todo_remove_done_items` additionally pins that no `pageerror` is raised during the interaction.
- [Queued refreshes on rapid mutations] → Each refresh reconciles from the current signal value (idempotent last-state-wins). Coalescing is explicitly out of scope (see Non-goals).
- [Exceptions in scheduled refreshes are logged, not raised] → `logging.error` keeps them visible in the browser console; E2E `assert_no_console_errors` (which matches Python traceback patterns) would still catch a refresh failure.
- [Behavioral divergence between Pyodide and server] → By design; server/test environments depend on synchronous refresh. The unit tests pin both branches.
