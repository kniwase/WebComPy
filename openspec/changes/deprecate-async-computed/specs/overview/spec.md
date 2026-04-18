## MODIFIED Requirements

### Requirement: Asynchronous operations shall integrate with the signal system
Developers SHALL be able to start async operations (HTTP requests, long computations) and have their results automatically reflected in the UI when they resolve, with loading and error states accessible through the signal system.

#### Scenario: Fetching data from an API
- **WHEN** a developer creates an `AsyncResult` via `useAsyncResult(fetch_func)` inside a component setup
- **THEN** the UI SHALL show a loading state (`AsyncResult.is_loading`) until the operation completes
- **AND** when the operation succeeds, the UI SHALL update with the result (`AsyncResult.data.value`)
- **AND** when the operation fails, the UI SHALL be able to detect the error (`AsyncResult.is_error`, `AsyncResult.error.value`)

## REMOVED Requirements

_None_