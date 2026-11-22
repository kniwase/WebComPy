# Delta: testing-module

## MODIFIED Requirements

### Requirement: webcompy.testing shall provide a run_sync helper for calling async code from sync contexts

`run_sync(coro)` SHALL execute an async coroutine from a synchronous context. It SHALL detect whether an event loop is already running in the current thread. If no loop is running, it SHALL use `asyncio.run(coro)`. If a loop IS running, it SHALL use `nest_asyncio2.apply(loop)` (patching the loop to allow re-entrant `run_until_complete`) and then `loop.run_until_complete(coro)`. This SHALL enable test utilities like `TestRenderer.render()` and `render_app_html()` to expose synchronous APIs while internally using async rendering.

#### Scenario: run_sync creates a new event loop when none is running
- **WHEN** `result = run_sync(async_fn())` is called outside any async context
- **THEN** `asyncio.run(coro)` SHALL be used internally
- **AND** the coroutine's return value SHALL be returned

#### Scenario: run_sync patches a running loop with nest_asyncio2
- **WHEN** `run_sync(async_fn())` is called inside a running event loop (e.g., inside a `pytest-asyncio` test)
- **THEN** `nest_asyncio2.apply()` SHALL be called on the current loop
- **AND** `loop.run_until_complete(coro)` SHALL be used

#### Scenario: Event loop shuts down cleanly on Python 3.14+ after run_sync patches a running loop
- **WHEN** `asyncio.run(...)` executes code that invokes `run_sync(async_fn())` on CPython 3.14+
- **THEN** `asyncio.run()` SHALL exit without raising `RuntimeError: Timeout should be used inside a task`
