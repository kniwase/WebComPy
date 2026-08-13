## MODIFIED Requirements

### Requirement: webcompy.testing package shall provide fake port implementations

`FakeBrowserHostPort` SHALL implement `HostPort` with `schedule_macro_task()` calling `callback()` synchronously and `create_js_global_getter()` returning a callable that returns `None`. `FakeBrowserHostPort.add_window_event_listener(event_type, handler)` SHALL record the handler per event type in an instance-local registry (no module-level state) and return an idempotent cleanup that removes exactly that handler; the fake SHALL expose a `dispatch_window_event(event_type, event)` helper that invokes the recorded handlers for the event type (snapshotting the list so handlers removed during dispatch are not invoked). `FakeBrowserDOMPort` SHALL inherit the server no-op `add_document_event_listener` behavior, SHALL override it to record handlers per event type with the same instance-local registry and idempotent cleanup semantics, and SHALL expose `dispatch_document_event(event_type, event)`. The no-op behavior of `ServerHostPort.add_window_event_listener` and `ServerDOMPort.add_document_event_listener` SHALL remain unchanged.

#### Scenario: FakeBrowserHostPort records and dispatches window listeners

- **WHEN** `FakeBrowserHostPort().add_window_event_listener("resize", handler)` is called
- **AND** `port.dispatch_window_event("resize", event)` is called
- **THEN** `handler` SHALL be invoked with the event
- **AND** calling the returned cleanup SHALL remove only that handler, so a subsequent dispatch does not invoke it

#### Scenario: FakeBrowserDOMPort records and dispatches document listeners

- **WHEN** `FakeBrowserDOMPort().add_document_event_listener("visibilitychange", handler)` is called
- **AND** `port.dispatch_document_event("visibilitychange", event)` is called
- **THEN** `handler` SHALL be invoked with the event
- **AND** the cleanup SHALL be idempotent (calling it twice SHALL NOT raise)

#### Scenario: Multiple listeners are dispatched independently

- **WHEN** two handlers are registered for the same event type
- **AND** one is removed before a dispatch
- **THEN** the dispatch SHALL invoke only the remaining handler

#### Scenario: Server no-op behavior is preserved

- **WHEN** `ServerHostPort().add_window_event_listener(...)` or `ServerDOMPort().add_document_event_listener(...)` is called
- **THEN** a no-op cleanup SHALL be returned and no handler SHALL be recorded
