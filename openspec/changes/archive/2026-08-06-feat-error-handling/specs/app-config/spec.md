# Delta: app-config

## ADDED Requirements

### Requirement: WebComPyAppConfig shall accept a global on_error handler

`WebComPyAppConfig` SHALL accept an optional `on_error: Callable[[Exception], Any] | None` field (default `None`). The handler SHALL be invoked for every error that completes the error-handling propagation walk unhandled (including event-handler errors not claimed by any `catch_events` boundary). When `on_error` is `None`, unhandled errors SHALL be logged (current behavior). Exceptions raised BY the `on_error` handler itself SHALL be logged and swallowed (the handler must never crash the app).

#### Scenario: Global handler receives uncontained error
- **WHEN** a component raises with no engaging boundary and `on_error` is configured
- **THEN** `on_error` SHALL be called with the exception exactly once per error

#### Scenario: Default logging preserved
- **WHEN** no `on_error` is configured and an uncontained error occurs
- **THEN** the error SHALL be logged (behavior unchanged from today)

#### Scenario: Handler exception is contained
- **WHEN** the `on_error` handler itself raises
- **THEN** the secondary exception SHALL be logged and SHALL NOT propagate
