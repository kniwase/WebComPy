## MODIFIED Requirements

### Requirement: useAsyncResult shall manage async operation results reactively
`useAsyncResult` SHALL accept an async function, execute it, and return an `AsyncResult` object with signal-based state, data, and error properties. It SHALL support automatic execution on rendering, signal-driven refetching, and manual refetching.

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

#### Scenario: Signal-driven refetching with watch
- **WHEN** a developer calls `useAsyncResult(fetch_search, watch=[query])` with `query` being a `Signal`
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
- **AND** the async function SHALL only execute when `refetch()` is called or a `watch` signal changes

#### Scenario: Watch cleanup on component destruction
- **WHEN** a component using `useAsyncResult` with `watch` is destroyed
- **THEN** all signal subscriptions registered on watched Signals SHALL be cleaned up via `consumer_destroy()`
- **AND** subsequent changes to watched Signals SHALL NOT trigger refetch