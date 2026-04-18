# Composables

## Purpose

Composables are reusable stateful logic functions that encapsulate reactive state and lifecycle behavior for use inside function-style component setup functions. They provide a composable alternative to class inheritance for sharing logic across components. Instead of extending a base class, a component calls composable functions during setup, and the returned reactive values integrate with the component's template and lifecycle.

WebComPy provides built-in composables (`useAsyncResult`, `useAsync`) for common async patterns, and standalone lifecycle decorators (`@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`) that register hooks implicitly via context variables.

## Requirements

### Requirement: Composables shall be reusable stateful logic functions
Composables SHALL be plain Python functions (or function calls) that encapsulate reactive state and lifecycle logic for use inside function-style component setup functions. They SHALL be callable inside a `@define_component` setup function and return values that integrate with the reactive system (Reactive, Computed, AsyncResult, etc.).

#### Scenario: Using a composable inside a component
- **WHEN** a developer calls a composable function inside a `@define_component` setup function
- **THEN** the returned reactive values SHALL be usable in the component's template
- **AND** any lifecycle hooks registered by the composable SHALL fire at the correct times

### Requirement: Standalone lifecycle hooks shall register without explicit context
`@on_before_rendering`, `@on_after_rendering`, and `@on_before_destroy` SHALL be module-level decorators that register lifecycle hooks using the active component context from `contextvars.ContextVar`. They SHALL NOT require an explicit `context` parameter.

#### Scenario: Registering an after-rendering hook with standalone decorator
- **WHEN** a developer decorates a function with `@on_after_rendering` inside a component setup function
- **THEN** the decorated function SHALL be called after the component renders
- **AND** the behavior SHALL be identical to calling `context.on_after_rendering(func)` explicitly

#### Scenario: Calling a standalone hook outside a component setup
- **WHEN** a developer calls `@on_after_rendering` outside of a component setup function
- **THEN** a `LookupError` SHALL be raised with a message indicating the function must be called inside a component setup context

#### Scenario: Nesting with child component instantiation
- **WHEN** a parent component setup function instantiates a child component (which also sets up its own context)
- **THEN** the parent's ContextVar SHALL be correctly restored after the child's setup completes
- **AND** lifecycle hooks registered in the parent's context SHALL not be affected by the child's context

### Requirement: useAsyncResult shall manage async operation results reactively
`useAsyncResult` SHALL accept an async function, execute it, and return an `AsyncResult` object with reactive state, data, and error properties. It SHALL support automatic execution on rendering, reactive-driven refetching, and manual refetching.

#### Scenario: Fetching data on component mount
- **WHEN** a developer calls `useAsyncResult(fetch_data, immediate=True)` inside a component setup
- **THEN** the async function SHALL be executed after the component renders
- **AND** `AsyncResult.state` SHALL transition from `PENDING` to `LOADING` to `SUCCESS` (or `ERROR`)
- **AND** `AsyncResult.data` SHALL contain the result on success

#### Scenario: Providing a default value
- **WHEN** a developer calls `useAsyncResult(fetch_list, default=[])` 
- **THEN** `AsyncResult.data.value` SHALL initially be `[]`
- **AND** after successful fetch, `data.value` SHALL contain the fetched list
- **AND** during refetch, `data.value` SHALL preserve the last successful value (SWR pattern)

#### Scenario: Reactive-driven refetching with watch
- **WHEN** a developer calls `useAsyncResult(fetch_search, watch=[query])` with `query` being a `Reactive`
- **THEN** whenever `query.value` changes, `refetch()` SHALL be called automatically
- **AND** the async function closure SHALL read the latest value of `query.value`

#### Scenario: Manual refetch triggering
- **WHEN** a developer calls `result.refetch()` or passes `result.refetch` as an event handler
- **THEN** the async function SHALL be re-executed
- **AND** `AsyncResult.state` SHALL transition to `LOADING` then to `SUCCESS` or `ERROR`
- **AND** extra positional arguments passed to `refetch` SHALL be ignored (allowing use as event handlers)

#### Scenario: Deferring execution with immediate=False
- **WHEN** a developer calls `useAsyncResult(fetch_data, immediate=False)`
- **THEN** the async function SHALL NOT be executed on component mount
- **AND** the async function SHALL only execute when `refetch()` is called or a `watch` reactive changes

#### Scenario: Watch cleanup on component destruction
- **WHEN** a component using `useAsyncResult` with `watch` is destroyed
- **THEN** all reactive subscriptions registered on watched Reactives SHALL be cleaned up via `consumer_destroy()`
- **AND** subsequent changes to watched Reactives SHALL NOT trigger refetch

### Requirement: AsyncResult shall provide structured async state
`AsyncResult` SHALL expose reactive state properties that enable declarative UI rendering of loading, success, and error states.

#### Scenario: Accessing reactive state predicates
- **WHEN** a developer accesses `result.is_loading`, `result.is_success`, `result.is_error`, or `result.is_pending`
- **THEN** each SHALL be a `Computed[bool]` that derives from `result.state`
- **AND** exactly one of `is_loading`, `is_success`, `is_error` SHALL be `True` at any time (mutually exclusive)
- **AND** `is_pending` SHALL be `True` only before the first execution

#### Scenario: Displaying different UI for each state
- **WHEN** a developer uses `switch()` with `result.is_loading`, `result.is_success`, and `result.is_error` as case conditions
- **THEN** the corresponding generator SHALL render for the current state
- **AND** transitions between states SHALL update the UI reactively

#### Scenario: Data preservation on error (SWR stale data)
- **WHEN** a successful fetch sets `data.value` to a result
- **AND** a subsequent refetch fails with an error
- **THEN** `data.value` SHALL retain the last successful value
- **AND** `state.value` SHALL be `AsyncState.ERROR`
- **AND** `error.value` SHALL contain the exception

### Requirement: useAsync shall execute side-effect-only async operations
`useAsync` SHALL accept an async function and execute it after the component renders. It SHALL NOT return a result object. It SHALL be used for fire-and-forget async operations.

#### Scenario: Triggering a side effect after rendering
- **WHEN** a developer calls `useAsync(send_analytics_event)` inside a component setup
- **THEN** the async function SHALL be executed after the component renders
- **AND** no return value SHALL be provided (the function returns `None`)

### Requirement: AsyncState shall enumerate async operation phases
`AsyncState` SHALL be a Python enum with four values: `PENDING` (not yet started), `LOADING` (in progress), `SUCCESS` (completed successfully), and `ERROR` (failed with an exception).

#### Scenario: State transitions during a typical fetch cycle
- **WHEN** `AsyncResult` is created with `immediate=False`
- **THEN** `state.value` SHALL be `AsyncState.PENDING`
- **WHEN** `refetch()` is called
- **THEN** `state.value` SHALL become `AsyncState.LOADING`
- **WHEN** the async function resolves successfully
- **THEN** `state.value` SHALL become `AsyncState.SUCCESS`
- **WHEN** the async function raises an exception
- **THEN** `state.value` SHALL become `AsyncState.ERROR`

### Requirement: AsyncResult shall be testable without component context
`AsyncResult` SHALL be constructable and usable outside of a component setup function. Its state machine, data preservation, and error handling SHALL work without a `contextvars.ContextVar` being set.

#### Scenario: Testing AsyncResult state transitions in unit tests
- **WHEN** a developer creates `AsyncResult(fetch_func)` outside a component
- **AND** calls `result.refetch()`
- **THEN** the state SHALL transition correctly (PENDING → LOADING → SUCCESS or ERROR)
- **AND** `data`, `error`, and computed predicates SHALL update accordingly