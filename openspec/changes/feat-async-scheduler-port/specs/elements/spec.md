## ADDED Requirements

### Requirement: DynamicElement._hydrate_node shall schedule via AsyncSchedulerPort

`DynamicElement._hydrate_node()` SHALL schedule the async render of unmounted children via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(child._render())` instead of calling `asyncio.ensure_future()` directly. The scheduled task SHALL be tracked in `self._pending_render_tasks` as before, and a done callback SHALL log exceptions via `webcompy.logging.error`. This routes all async scheduling through the central port, ensuring server-side renders guarantee task completion before context disposal.

#### Scenario: Hydrating an unmounted child via the scheduler port
- **WHEN** `DynamicElement._hydrate_node()` encounters a child that is not mounted
- **THEN** the child's `_render()` coroutine SHALL be scheduled via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(child._render())`
- **AND** the returned task SHALL be appended to `self._pending_render_tasks`
- **AND** a done callback SHALL be attached that logs exceptions and removes the task from `_pending_render_tasks`

### Requirement: SuspenseElement shall schedule browser resolution via AsyncSchedulerPort

`SuspenseElement._browser_render()` and `SuspenseElement._hydrate_node()` SHALL schedule async resolution coroutines via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(coro)` instead of calling `asyncio.ensure_future()` directly. The scheduled task SHALL be tracked in `self._pending_tasks` as before.

#### Scenario: Suspense schedules browser resolution via the scheduler port
- **WHEN** `SuspenseElement._browser_render()` determines that children have unresolved async setup
- **THEN** the resolution coroutine SHALL be scheduled via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(self._browser_resolve(...))`
- **AND** the returned task SHALL be appended to `self._pending_tasks`

#### Scenario: Suspense hydrate schedules resolution via the scheduler port
- **WHEN** `SuspenseElement._hydrate_node()` determines that children lack resolved data
- **THEN** the resolution coroutine SHALL be scheduled via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(self._browser_resolve())`
- **AND** the returned task SHALL be appended to `self._pending_tasks`
