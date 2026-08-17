# Async Scheduler — Render-Task Scoping Deltas

## MODIFIED Requirements

### Requirement: The scheduler port shall distinguish render tasks for hydration draining

`AsyncSchedulerPort.schedule(coro)` SHALL accept an optional keyword flag `render: bool = False`. Tasks scheduled with `render=True` are render/hydration tasks that MUST complete before the browser hydration reveal; tasks scheduled without the flag (generic `aio_run` work) are ordinary fire-and-forget tasks. `AsyncSchedulerPort.await_pending()` SHALL accept an optional keyword flag `only_render: bool = False`.

`BrowserAsyncSchedulerPort.await_pending(only_render=True)` SHALL await completion of the `render=True` tasks that have not yet completed, excluding the current task and re-checking for tasks scheduled during the drain (recursive scheduling), with the same max-iteration guard as the server port. Tasks scheduled without `render=True` SHALL NOT block this call. `BrowserAsyncSchedulerPort.await_pending()` (no arguments) SHALL await all registered tasks. A render-only drain SHALL NOT unregister non-render tasks: tasks scheduled without `render=True` SHALL remain registered so that a later `await_pending()` call (without arguments) can still await them. Exceptions raised by scheduled tasks SHALL NOT propagate through `await_pending()`.

`ServerAsyncSchedulerPort.schedule(coro)` SHALL accept the same `render` flag (ignored: the server drains all registered tasks before context disposal) and `ServerAsyncSchedulerPort.await_pending()` SHALL accept `only_render` (ignored). `FakeAsyncSchedulerPort` SHALL track the flag and SHALL filter on `await_pending(only_render=True)` while `drain()` continues to execute all collected coroutines.

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

#### Scenario: Fake port honors the render flag
- **WHEN** a test schedules one plain task and one `render=True` task on `FakeAsyncSchedulerPort`
- **AND** `await_pending(only_render=True)` is called
- **THEN** only the render-marked coroutine SHALL execute
- **AND** the plain coroutine SHALL remain collected for a later drain

#### Scenario: Render-only drain keeps non-render tasks registered
- **WHEN** a plain task and a `render=True` task are scheduled on `BrowserAsyncSchedulerPort`
- **AND** `await_pending(only_render=True)` is called
- **THEN** the plain task SHALL NOT be awaited by that call
- **AND** the plain task SHALL remain in the scheduler's registry
- **AND** a subsequent `await_pending()` (no arguments) SHALL await the plain task