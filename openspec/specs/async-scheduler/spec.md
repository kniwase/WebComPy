# Async Scheduler Port

## Purpose

The `AsyncSchedulerPort` centralizes all async coroutine scheduling behind a single typed, injectable port. The browser implementation is fire-and-forget (the event loop is long-lived), while the server implementation registers scheduled tasks in a per-request registry and drains them before the render context is disposed. This structurally eliminates the class of dual-environment lifecycle bugs where fire-and-forget tasks outlive the DI scope on the server.

## Requirements

### Requirement: AsyncSchedulerPort shall provide a unified async task scheduling interface

The framework SHALL provide an `AsyncSchedulerPort` abstract base class that centralizes all async coroutine scheduling. The port SHALL define two methods: `schedule(coro: Coroutine[Any, Any, Any], *, render: bool = False) -> asyncio.Task[Any]` for scheduling a coroutine as a task, and `await_pending(*, only_render: bool = False) -> Awaitable[None]` for awaiting the completion of all scheduled tasks. The port SHALL be injectable via `ASYNC_SCHEDULER_PORT_KEY: InjectKey[AsyncSchedulerPort]`.

Tasks scheduled with `render=True` are render/hydration tasks that MUST complete before the browser hydration reveal; tasks scheduled without the flag (generic `aio_run` work) are ordinary fire-and-forget tasks. `await_pending(only_render=True)` SHALL await only the render-marked tasks.

#### Scenario: Scheduling a coroutine during render
- **WHEN** any framework code needs to schedule an async task during the render pipeline
- **THEN** the code SHALL call `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(coro)` instead of `asyncio.ensure_future(coro)` or `loop.create_task(coro)`
- **AND** hydration/render tasks SHALL pass `render=True` so the browser hydration drain can await them

#### Scenario: Injecting the scheduler port
- **WHEN** a `RenderContext` is created in either browser or server environment
- **THEN** the context's DI scope SHALL provide an `AsyncSchedulerPort` instance via `ASYNC_SCHEDULER_PORT_KEY`

### Requirement: BrowserAsyncSchedulerPort shall use fire-and-forget scheduling

`BrowserAsyncSchedulerPort.schedule(coro)` SHALL create a task via `asyncio.ensure_future(coro)`, register it in the port's internal task registry together with its `render` flag, and return it. The task runs on the browser's long-lived event loop and completes naturally. `BrowserAsyncSchedulerPort.await_pending(only_render=True)` SHALL await completion of the `render=True` tasks that have not yet completed, excluding the current task and re-checking for tasks scheduled during the drain (recursive scheduling), with the same max-iteration guard as the server port. Tasks scheduled without `render=True` SHALL NOT block this call. `BrowserAsyncSchedulerPort.await_pending()` (no arguments) SHALL await all registered tasks. A render-only drain SHALL NOT unregister non-render tasks: tasks scheduled without `render=True` SHALL remain registered so that a later `await_pending()` call (without arguments) can still await them. Exceptions raised by scheduled tasks SHALL NOT propagate through `await_pending()`.

#### Scenario: Browser schedules a fire-and-forget task
- **WHEN** `BrowserAsyncSchedulerPort.schedule(coro)` is called
- **THEN** an `asyncio.Task` SHALL be created via `asyncio.ensure_future`
- **AND** the task SHALL be registered in the port's registry (with its `render` flag)
- **AND** the task SHALL complete on the browser event loop

#### Scenario: Browser hydration drain awaits only render-marked tasks
- **WHEN** browser hydration schedules render tasks via `schedule(coro, render=True)`
- **AND** a non-render user task is also pending
- **AND** `await_pending(only_render=True)` is called
- **THEN** the call SHALL await only the render-marked tasks
- **AND** the call SHALL NOT wait for the non-render task

#### Scenario: Recursive render scheduling is drained
- **WHEN** a render-marked task schedules another render-marked task before completing
- **AND** `await_pending(only_render=True)` is called
- **THEN** the newly scheduled render task SHALL also complete before the call returns

#### Scenario: Render-only drain keeps non-render tasks registered
- **WHEN** a plain task and a `render=True` task are scheduled on `BrowserAsyncSchedulerPort`
- **AND** `await_pending(only_render=True)` is called
- **THEN** the plain task SHALL NOT be awaited by that call
- **AND** the plain task SHALL remain in the scheduler's registry
- **AND** a subsequent `await_pending()` (no arguments) SHALL await the plain task

### Requirement: ServerAsyncSchedulerPort shall register and drain tasks

`ServerAsyncSchedulerPort.schedule(coro)` SHALL create a task via `loop.create_task(coro)`, register it in an internal per-instance registry (`_registry: list[asyncio.Task]`), and return the task. The `render` flag SHALL be accepted and ignored: the server drains all registered tasks before context disposal regardless of the flag. `ServerAsyncSchedulerPort.await_pending()` SHALL accept `only_render` (ignored). `await_pending()` SHALL gather all tasks currently in the registry, awaiting their completion. After `await_pending()` returns, the registry SHALL be empty (all tasks completed or cancelled).

#### Scenario: Server registers a scheduled task
- **WHEN** `ServerAsyncSchedulerPort.schedule(coro)` is called
- **THEN** a task SHALL be created via `loop.create_task(coro)`
- **AND** the task SHALL be appended to the port instance's `_registry` list
- **AND** the task reference SHALL be returned to the caller

#### Scenario: Server drains all pending tasks
- **WHEN** `ServerAsyncSchedulerPort.await_pending()` is called
- **THEN** a snapshot of `_registry` SHALL be taken via `list(self._registry)` before iteration
- **AND** the snapshot tasks SHALL be awaited via `asyncio.gather`
- **AND** concurrent `done_callback` removals SHALL NOT cause iteration errors (the snapshot is independent of the live list)
- **AND** tasks that complete during the gather SHALL be removed from `_registry`
- **AND** after `await_pending()` returns, `_registry` SHALL be empty

#### Scenario: Server handles tasks scheduled during drain
- **WHEN** a task scheduled via `schedule()` itself schedules additional tasks (recursive scheduling)
- **AND** `await_pending()` is called
- **THEN** `await_pending()` SHALL re-check the registry after the initial gather completes
- **AND** if newly added tasks exist, they SHALL be gathered in a subsequent iteration
- **AND** this loop SHALL continue until the registry is empty or a maximum iteration guard of 20 is reached
- **AND** when the guard is reached, a warning SHALL be logged indicating a possible recursive scheduling bug

### Requirement: aio_run shall delegate to AsyncSchedulerPort when a DI scope is active

The `aio_run` function (environment-selected from `_aio_run_browser` and `_aio_run_server`) SHALL attempt `inject(ASYNC_SCHEDULER_PORT_KEY)` at call time. If injection succeeds, the coroutine SHALL be scheduled via `scheduler.schedule(coro)`. If injection fails (no active DI scope), the fallback SHALL create the task directly (`asyncio.ensure_future` on browser, `loop.create_task` on server) and SHALL log a warning indicating the task may not be awaited on the server.

#### Scenario: aio_run within a render context
- **WHEN** `aio_run(coro)` is called during a render (DI scope active)
- **THEN** the coroutine SHALL be scheduled via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(coro)`
- **AND** on the server, the task SHALL be registered in the scheduler's registry

#### Scenario: aio_run outside a render context
- **WHEN** `aio_run(coro)` is called outside any DI scope (e.g., in CLI utilities)
- **THEN** the fallback SHALL create the task directly via `asyncio.ensure_future` or `loop.create_task`
- **AND** a warning SHALL be logged indicating the task is not registry-tracked

### Requirement: No bare asyncio scheduling shall exist outside AsyncSchedulerPort

The framework codebase SHALL NOT contain direct `asyncio.ensure_future()` or `asyncio.get_event_loop().create_task()` calls in the `webcompy`, `webcompy-server`, or `webcompy-cli` packages, except within `AsyncSchedulerPort` implementations and the `aio_run` fallback path. All async task scheduling SHALL route through `AsyncSchedulerPort.schedule()` or `aio_run()`. This invariant SHALL be enforced by CI review.

#### Scenario: Code review detects bare ensure_future
- **WHEN** a pull request introduces a new `asyncio.ensure_future()` call outside `AsyncSchedulerPort` implementations or `aio_run`
- **THEN** the CI review SHALL flag it as an invariant violation

### Requirement: A FakeAsyncSchedulerPort shall be provided for testing

The `webcompy_testing` module SHALL provide a `FakeAsyncSchedulerPort` that collects scheduled coroutines in a list without executing them. The port SHALL track the `render` flag for each scheduled coroutine. `await_pending(only_render=True)` SHALL execute only the render-marked coroutines, leaving the plain coroutines collected; `await_pending()` (no arguments) and `drain()` SHALL execute all collected coroutines. `drain()` and `await_pending()` SHALL re-check for coroutines scheduled by the coroutines they execute, continuing until no matching coroutines remain (recursive scheduling), with a maximum-iteration guard that logs a warning when exceeded. Executed coroutines SHALL settle their placeholder tasks: the placeholder SHALL be marked done, the executed coroutine's exception (if any) SHALL be recorded and returned by `exception()`, and registered done callbacks SHALL be invoked. Cancelling a placeholder whose coroutine has already been executed SHALL return `False` and SHALL be a no-op. Tests SHALL be able to call `await fake_scheduler.drain()` to execute all collected coroutines, or inspect the list to assert scheduling behavior.

#### Scenario: Fake port collects scheduled coroutines
- **WHEN** `FakeAsyncSchedulerPort.schedule(coro)` is called
- **THEN** the coroutine SHALL be appended to an internal list without execution
- **AND** a dummy `asyncio.Task` or placeholder SHALL be returned

#### Scenario: Fake port drains collected coroutines
- **WHEN** `await fake_scheduler.drain()` is called
- **THEN** all collected coroutines SHALL be executed via `asyncio.gather`
- **AND** the internal list SHALL be cleared

#### Scenario: Fake port honors the render flag
- **WHEN** a test schedules one plain task and one `render=True` task on `FakeAsyncSchedulerPort`
- **AND** `await_pending(only_render=True)` is called
- **THEN** only the render-marked coroutine SHALL execute
- **AND** the plain coroutine SHALL remain collected for a later drain

#### Scenario: Fake port drains recursively scheduled coroutines
- **WHEN** a scheduled coroutine schedules another coroutine before completing
- **AND** `drain()` (or `await_pending(only_render=True)` for render-marked coroutines) is called
- **THEN** the newly scheduled coroutine SHALL also execute before the call returns

#### Scenario: Fake port settles executed placeholders
- **WHEN** a scheduled coroutine has completed during `drain()` or `await_pending()`
- **THEN** its placeholder SHALL be marked done
- **AND** registered done callbacks SHALL be invoked with the placeholder
- **AND** if the coroutine raised, the exception SHALL be returned by `exception()`

#### Scenario: Cancelling an executed placeholder is a no-op
- **WHEN** a placeholder's coroutine has already been executed during a drain
- **AND** `cancel()` is called on the placeholder
- **THEN** `cancel()` SHALL return `False`
- **AND** the placeholder SHALL NOT be marked cancelled
