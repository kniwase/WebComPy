# Port Abstraction Specification (delta)

## ADDED Requirements

### Requirement: WebSocketPort ABC shall exist in the port hierarchy

The framework SHALL provide a `WebSocketPort` abstract base class in `webcompy.ports` for the WebSocket browser API surface. It SHALL define methods for opening a WebSocket connection to a URL with optional subprotocols, delivering received messages and connection-lifecycle transitions to caller-supplied callbacks, sending text frames, and closing the connection. The port SHALL be callback-based and SHALL NOT import `Component` or any component module; all knowledge of subscribers SHALL be supplied as callables at open time.

#### Scenario: WebSocketPort is importable

- **WHEN** a developer imports `webcompy.ports`
- **THEN** `WebSocketPort` SHALL be accessible

#### Scenario: WebSocketPort cannot be instantiated directly

- **WHEN** a developer attempts to instantiate `WebSocketPort` directly
- **THEN** Python SHALL raise `TypeError` due to abstract methods

#### Scenario: Browser implementation wraps native WebSocket

- **WHEN** the browser `WebSocketPort` opens a connection
- **THEN** it SHALL construct a native `WebSocket` for the given URL and protocols, forward message/close/error events to the supplied callbacks, and expose send/close operations on the returned handle
- **AND** closing the handle SHALL close the native socket and remove its listeners

#### Scenario: Port does not depend on the component module

- **WHEN** the websocket port module is imported
- **THEN** it SHALL not import `webcompy.components._component` or any component class
