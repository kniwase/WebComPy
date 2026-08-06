## ADDED Requirements

### Requirement: Framework validation errors shall bypass error routing

`WebComPyException` (framework validation, e.g. duplicate `repeat()` keys) SHALL NOT enter the error-boundary propagation walk. It SHALL propagate as a hard failure directly to the caller, bypassing `on_error_captured` hooks, `ErrorBoundary` engagement, and the global error handler.

#### Scenario: Duplicate repeat key propagates as hard failure

- **WHEN** a `repeat()` key function returns the same key for two items inside an `ErrorBoundary`
- **THEN** the `WebComPyException` SHALL propagate past the boundary without engaging its fallback
- **AND** `on_error` on any boundary SHALL NOT be invoked for this error
