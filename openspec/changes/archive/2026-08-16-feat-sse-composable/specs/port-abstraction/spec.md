# Port Abstraction Specification (delta)

## ADDED Requirements

### Requirement: EventSourcePort ABC shall exist in the port hierarchy

The framework SHALL provide an `EventSourcePort` abstract base class in `webcompy.ports` for the Server-Sent Events browser API surface. It SHALL define a method for opening an SSE connection to a URL for a set of named event types, delivering received events and connection-lifecycle transitions to caller-supplied callbacks, and returning a cleanup function that closes the connection. The port SHALL be callback-based and SHALL NOT import `Component` or any component module; all knowledge of subscribers SHALL be supplied as callables at open time.

#### Scenario: EventSourcePort is importable

- **WHEN** a developer imports `webcompy.ports`
- **THEN** `EventSourcePort` SHALL be accessible

#### Scenario: EventSourcePort cannot be instantiated directly

- **WHEN** a developer attempts to instantiate `EventSourcePort` directly
- **THEN** Python SHALL raise `TypeError` due to abstract methods

#### Scenario: Browser implementation wraps native EventSource

- **WHEN** the browser `EventSourcePort` opens a connection
- **THEN** it SHALL construct a native `EventSource` for the given URL, register listeners for the requested event types, and forward events to the supplied callbacks
- **AND** the returned cleanup SHALL close the native connection and remove the listeners

#### Scenario: Port does not depend on the component module

- **WHEN** the event-source port module is imported
- **THEN** it SHALL not import `webcompy.components._component` or any component class
