## MODIFIED Requirements

### Requirement: use_async_result shall manage async operation results reactively
`use_async_result` SHALL accept an async function, execute it, and return an `AsyncResult` object with signal state, data, and error properties. It SHALL support automatic execution on rendering, reactive-driven refetching, and manual refetching.

#### Scenario: Fetching data on component mount
- **WHEN** a developer calls `use_async_result(fetch_data, immediate=True)` inside a component setup
- **THEN** the async function SHALL be executed after the component renders
- **AND** `AsyncResult.state` SHALL transition from `PENDING` to `LOADING` to `SUCCESS` (or `ERROR`)
- **AND** `AsyncResult.data` SHALL contain the result on success

#### Scenario: Providing a default value
- **WHEN** a developer calls `use_async_result(fetch_list, default=[])` 
- **THEN** `AsyncResult.data.value` SHALL initially be `[]`
- **AND** after successful fetch, `data.value` SHALL contain the fetched list
- **AND** during refetch, `data.value` SHALL preserve the last successful value (SWR pattern)

#### Scenario: Signal-driven refetching with watch
- **WHEN** a developer calls `use_async_result(fetch_search, watch=[query])` with `query` being a `Signal`
- **THEN** whenever `query.value` changes, `refetch()` SHALL be called automatically
- **AND** the async function closure SHALL read the latest value of `query.value`

#### Scenario: Manual refetch triggering
- **WHEN** a developer calls `result.refetch()` or passes `result.refetch` as an event handler
- **THEN** the async function SHALL be re-executed
- **AND** `AsyncResult.state` SHALL transition to `LOADING` then to `SUCCESS` or `ERROR`
- **AND** extra positional arguments passed to `refetch` SHALL be ignored (allowing use as event handlers)

#### Scenario: Deferring execution with immediate=False
- **WHEN** a developer calls `use_async_result(fetch_data, immediate=False)`
- **THEN** the async function SHALL NOT be executed on component mount
- **AND** the async function SHALL only execute when `refetch()` is called or a `watch` signal changes

#### Scenario: Watch cleanup on component destruction
- **WHEN** a component using `use_async_result` with `watch` is destroyed
- **THEN** all reactive subscriptions registered on watched Signals SHALL be cleaned up via `consumer_destroy()`
- **AND** subsequent changes to watched Signals SHALL NOT trigger refetch

### Requirement: use_async shall execute side-effect-only async operations
`use_async` SHALL accept an async function and execute it after the component renders. It SHALL NOT return a result object. It SHALL be used for fire-and-forget async operations.

#### Scenario: Triggering a side effect after rendering
- **WHEN** a developer calls `use_async(send_analytics_event)` inside a component setup
- **THEN** the async function SHALL be executed after the component renders
- **AND** no return value SHALL be provided (the function returns `None`)

### Requirement: use_router shall provide typed router access via DI
`use_router()` SHALL be a composable function that returns the Router instance by calling `inject()` with the framework's router DI key. It SHALL raise `InjectionError` if no router is provided (i.e., the app was created without a router).

#### Scenario: Using use_router in a component
- **WHEN** a component setup function calls `use_router()`
- **AND** the app was created with a router
- **THEN** the Router instance SHALL be returned

#### Scenario: Using use_router without a router
- **WHEN** a component setup function calls `use_router()`
- **AND** the app was created without a router
- **THEN** `InjectionError` SHALL be raised

#### Scenario: use_router is a thin inject wrapper
- **WHEN** a developer inspects the `use_router` implementation
- **THEN** it SHALL be equivalent to `return inject(RouterKey)` where `RouterKey` is the framework's public router DI key
