# Port Provisioning Specification (delta)

## ADDED Requirements

### Requirement: WEBSOCKET_PORT_KEY shall live in core keys

The framework SHALL define `WEBSOCKET_PORT_KEY: InjectKey[WebSocketPort]` in `packages/webcompy/src/webcompy/ports/_keys.py` alongside the existing port keys.

#### Scenario: Key importable from core

- **WHEN** a developer writes `from webcompy.ports._keys import WEBSOCKET_PORT_KEY`
- **THEN** the key SHALL be importable without installing `webcompy-server`

### Requirement: All render contexts shall provision a WebSocketPort

The browser render context SHALL provide a browser `WebSocketPort` implementation via `WEBSOCKET_PORT_KEY`. The server render context SHALL provide a no-op implementation that never accesses browser APIs or creates FFI proxies. The testing render path SHALL provide a fake implementation that records connections and delivers scripted messages.

#### Scenario: Browser context provisions the browser port

- **WHEN** a `BrowserRenderContext` is created
- **THEN** `WEBSOCKET_PORT_KEY` SHALL resolve to a browser websocket port
- **AND** the port SHALL be able to open native `WebSocket` connections

#### Scenario: Server context provisions a no-op port

- **WHEN** a `ServerRenderContext` is created
- **THEN** `WEBSOCKET_PORT_KEY` SHALL resolve to a no-op port
- **AND** its open/send/close methods SHALL not access browser APIs and SHALL be safe to call

#### Scenario: Testing path provisions a fake port

- **WHEN** the testing render path provisions ports
- **THEN** `WEBSOCKET_PORT_KEY` SHALL resolve to a fake implementation
- **AND** unit tests SHALL run without a browser or PyScript runtime
