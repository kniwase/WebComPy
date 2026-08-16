# Port Provisioning Specification (delta)

## ADDED Requirements

### Requirement: EVENT_SOURCE_PORT_KEY shall live in core keys

The framework SHALL define `EVENT_SOURCE_PORT_KEY: InjectKey[EventSourcePort]` in `packages/webcompy/src/webcompy/ports/_keys.py` alongside the existing port keys.

#### Scenario: Key importable from core

- **WHEN** a developer writes `from webcompy.ports._keys import EVENT_SOURCE_PORT_KEY`
- **THEN** the key SHALL be importable without installing `webcompy-server`

### Requirement: All render contexts shall provision an EventSourcePort

The browser render context SHALL provide a browser `EventSourcePort` implementation via `EVENT_SOURCE_PORT_KEY`. The server render context SHALL provide a no-op implementation that never accesses browser APIs or creates FFI proxies. The testing render path SHALL provide a fake implementation that records subscriptions and delivers scripted events.

#### Scenario: Browser context provisions the browser port

- **WHEN** a `BrowserRenderContext` is created
- **THEN** `EVENT_SOURCE_PORT_KEY` SHALL resolve to a browser event-source port
- **AND** the port SHALL be able to open native `EventSource` connections

#### Scenario: Server context provisions a no-op port

- **WHEN** a `ServerRenderContext` is created
- **THEN** `EVENT_SOURCE_PORT_KEY` SHALL resolve to a no-op port
- **AND** calling its open method SHALL not access browser APIs and SHALL return a no-op cleanup
- **AND** the port SHALL be marked no-op (`noop`) so the composable can distinguish it from real ports (e.g., testing fakes) resolved outside the browser

#### Scenario: Testing path provisions a fake port

- **WHEN** the testing render path provisions ports
- **THEN** `EVENT_SOURCE_PORT_KEY` SHALL resolve to a fake implementation
- **AND** unit tests SHALL run without a browser or PyScript runtime
