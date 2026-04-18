## MODIFIED Requirements

### Requirement: Async operations shall integrate with the reactive system
Developers SHALL be able to create a reactive value that starts unresolved and automatically updates when an async operation completes, triggering UI updates like any other reactive change.

#### Scenario: Loading data from an API on component mount with useAsyncResult
- **WHEN** a developer calls `useAsyncResult(fetch_func)` inside a component setup
- **THEN** `result.state` SHALL initially be `AsyncState.PENDING`
- **AND** after rendering, `result.state` SHALL transition to `AsyncState.LOADING`
- **WHEN** the async function resolves successfully
- **THEN** `result.data.value` SHALL contain the result
- **AND** `result.state.value` SHALL be `AsyncState.SUCCESS`
- **AND** `result.is_success.value` SHALL be `True`
- **AND** the UI SHALL update automatically

#### Scenario: Handling an async operation failure with structured error state
- **WHEN** the async function raises an exception
- **THEN** `result.state.value` SHALL be `AsyncState.ERROR`
- **AND** `result.is_error.value` SHALL be `True`
- **AND** `result.error.value` SHALL contain the exception
- **AND** `result.data.value` SHALL retain the last successful value (SWR pattern) or be the `default` value if no prior success

#### Scenario: Distinguishing async states with AsyncResult predicates
- **WHEN** a developer checks `result.is_pending`, `result.is_loading`, `result.is_success`, or `result.is_error`
- **THEN** each SHALL be a `Computed[bool]` reflecting the current `AsyncResult.state`
- **AND** they SHALL be suitable for use as `switch()` case conditions
- **AND** `result.is_loading` and `result.is_success` SHALL be mutually exclusive after the first execution

## ADDED Requirements

### Requirement: AsyncComputed and AsyncWrapper shall be deprecated in favor of composable async patterns
`AsyncComputed` and `AsyncWrapper` SHALL continue to function but SHALL emit `DeprecationWarning` when used. Developers SHALL be directed to use `useAsyncResult` or `useAsync` instead.

#### Scenario: Deprecation warning for AsyncComputed
- **WHEN** a developer creates an `AsyncComputed` instance
- **THEN** a `DeprecationWarning` SHALL be emitted
- **AND** the instance SHALL continue to function as before

#### Scenario: Deprecation warning for AsyncWrapper
- **WHEN** a developer uses `@AsyncWrapper()` decorator
- **THEN** a `DeprecationWarning` SHALL be emitted
- **AND** the decorated function SHALL continue to function as before