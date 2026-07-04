## ADDED Requirements

### Requirement: AsyncSchedulerPort shall provide a unified async task scheduling interface

The framework SHALL provide an `AsyncSchedulerPort` abstract base class that centralizes all async coroutine scheduling. The port SHALL define two methods: `schedule(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]` for scheduling a coroutine as a task, and `await_pending() -> Awaitable[None]` for awaiting the completion of all scheduled tasks. The port SHALL be injectable via `ASYNC_SCHEDULER_PORT_KEY: InjectKey[AsyncSchedulerPort]`.

#### Scenario: Scheduling a coroutine during render
- **WHEN** any framework code needs to schedule an async task during the render pipeline
- **THEN** the code SHALL call `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(coro)` instead of `asyncio.ensure_future(coro)` or `loop.create_task(coro)`

#### Scenario: Injecting the scheduler port
- **WHEN** a `RenderContext` is created in either browser or server environment
- **THEN** the context's DI scope SHALL provide an `AsyncSchedulerPort` instance via `ASYNC_SCHEDULER_PORT_KEY`

### Requirement: BrowserAsyncSchedulerPort shall use fire-and-forget scheduling

`BrowserAsyncSchedulerPort.schedule(coro)` SHALL create a task via `asyncio.ensure_future(coro)` and return it. The task runs on the browser's long-lived event loop and completes naturally. `BrowserAsyncSchedulerPort.await_pending()` SHALL be a no-op (returns immediately without awaiting), because the browser event loop persists for the page lifetime.

#### Scenario: Browser schedules a fire-and-forget task
- **WHEN** `BrowserAsyncSchedulerPort.schedule(coro)` is called
- **THEN** an `asyncio.Task` SHALL be created via `asyncio.ensure_future`
- **AND** the task SHALL NOT be explicitly awaited by the scheduler
- **AND** the task SHALL complete on the browser event loop

#### Scenario: Browser await_pending is a no-op
- **WHEN** `BrowserAsyncSchedulerPort.await_pending()` is called
- **THEN** the method SHALL return immediately without blocking
- **AND** no tasks SHALL be gathered or awaited

### Requirement: ServerAsyncSchedulerPort shall register and drain tasks

`ServerAsyncSchedulerPort.schedule(coro)` SHALL create a task via `loop.create_task(coro)`, register it in an internal per-instance registry (`_registry: list[asyncio.Task]`), and return the task. `ServerAsyncSchedulerPort.await_pending()` SHALL gather all tasks currently in the registry, awaiting their completion. After `await_pending()` returns, the registry SHALL be empty (all tasks completed or cancelled).

#### Scenario: Server registers a scheduled task
- **WHEN** `ServerAsyncSchedulerPort.schedule(coro)` is called
- **THEN** a task SHALL be created via `loop.create_task(coro)`
- **AND** the task SHALL be appended to the port instance's `_registry` list
- **AND** the task reference SHALL be returned to the caller

#### Scenario: Server drains all pending tasks
- **WHEN** `ServerAsyncSchedulerPort.await_pending()` is called
- **THEN** all tasks in `_registry` SHALL be awaited via `asyncio.gather`
- **AND** tasks that complete during the gather SHALL be removed from `_registry`
- **AND** after `await_pending()` returns, `_registry` SHALL be empty

#### Scenario: Server handles tasks scheduled during drain
- **WHEN** a task scheduled via `schedule()` itself schedules additional tasks (recursive scheduling)
- **AND** `await_pending()` is called
- **THEN** `await_pending()` SHALL re-check the registry after the initial gather completes
- **AND** if newly added tasks exist, they SHALL be gathered in a subsequent iteration
- **AND** this loop SHALL continue until the registry is empty or a maximum iteration guard is reached

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

The framework codebase SHALL NOT contain direct `asyncio.ensure_future()` or `asyncio.get_event_loop().create_task()` calls in the `webcompy`, `webcompy-server`, or `webcompy-cli` packages, except within `AsyncSchedulerPort` implementations and the `aio_run` fallback path. All async task scheduling SHALL route through `AsyncSchedulerPort.schedule()` or `aio_run()`. This invariant SHALL be enforced by the `ci-review` agent.

#### Scenario: Code review detects bare ensure_future
- **WHEN** a pull request introduces a new `asyncio.ensure_future()` call outside `AsyncSchedulerPort` implementations or `aio_run`
- **THEN** the CI review SHALL flag it as an invariant violation

### Requirement: A FakeAsyncSchedulerPort shall be provided for testing

The `webcompy_testing` module SHALL provide a `FakeAsyncSchedulerPort` that collects scheduled coroutines in a list without executing them. Tests SHALL be able to call `await fake_scheduler.drain()` to execute all collected coroutines, or inspect the list to assert scheduling behavior.

#### Scenario: Fake port collects scheduled coroutines
- **WHEN** `FakeAsyncSchedulerPort.schedule(coro)` is called
- **THEN** the coroutine SHALL be appended to an internal list without execution
- **AND** a dummy `asyncio.Task` or placeholder SHALL be returned

#### Scenario: Fake port drains collected coroutines
- **WHEN** `await fake_scheduler.drain()` is called
- **THEN** all collected coroutines SHALL be executed via `asyncio.gather`
- **AND** the internal list SHALL be cleared
