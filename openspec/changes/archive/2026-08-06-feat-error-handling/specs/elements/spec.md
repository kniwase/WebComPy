# Delta: elements

## ADDED Requirements

### Requirement: Event-handler invocation shall be wrapped for error routing

The framework's event-handler wrapper (`_generate_event_handler`) SHALL catch exceptions from both sync handlers and async handlers (via the `resolve_async` error path). Caught errors SHALL enter the error-handling propagation walk starting at the element the handler is attached to: `catch_events=True` boundaries engage; otherwise the error reaches `AppConfig.on_error` or is logged. Handler wrapping SHALL NOT change the existing `create_proxy`/`destroy` lifecycle — proxies are still created once and destroyed on removal.

#### Scenario: Sync handler error is routed
- **WHEN** a sync `on_click` handler raises
- **THEN** the exception SHALL NOT escape into the PyScript proxy uncaught
- **AND** it SHALL be delivered to the propagation walk (global handler or `catch_events` boundary)

#### Scenario: Async handler error is routed
- **WHEN** an async event handler's coroutine raises
- **THEN** the error SHALL be routed identically to sync handler errors (not merely logged by `resolve_async`'s default)

#### Scenario: Proxy lifecycle unchanged
- **WHEN** an element with event handlers is removed
- **THEN** its proxies SHALL still be destroyed exactly as today (no leak introduced by wrapping)
