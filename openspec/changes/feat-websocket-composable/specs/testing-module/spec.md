# Testing Module Specification (delta)

## ADDED Requirements

### Requirement: webcompy.testing package shall provide a FakeWebSocketPort

`FakeWebSocketPort` SHALL implement `WebSocketPort` with an instance-local registry of open connections (no module-level state). Opening a connection SHALL record the supplied callbacks keyed by `(url, protocols)` and SHALL return a fake handle whose `send(text)` records sent frames and whose `close()` unregisters the connection idempotently. The fake SHALL expose scripted-delivery helpers (e.g., `emit_message(url, text)` plus open/error/close lifecycle helpers carrying close code/reason) that invoke the recorded callbacks for matching registrations, snapshotting the callback list so registrations removed during delivery are not invoked. The fake SHALL NOT construct any native or network object.

#### Scenario: Scripted message delivery reaches subscribers

- **WHEN** `FakeWebSocketPort()` opens a connection for `"/ws"` with a message callback
- **AND** `port.emit_message("/ws", "hello")` is called
- **THEN** the recorded callback SHALL be invoked with `"hello"`
- **AND** no real network access SHALL occur

#### Scenario: Sent frames are recorded for assertions

- **WHEN** a test sends `handle.send("ping")` through the fake
- **THEN** the fake SHALL record `"ping"` in that connection's sent-frames log

#### Scenario: Scripted close carries code and reason

- **WHEN** `port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)` is called
- **THEN** the recorded close callback SHALL receive the code, reason, and cleanliness

#### Scenario: Cleanup is idempotent and instance-local

- **WHEN** a connection's `close()` is called twice
- **THEN** no exception SHALL be raised
- **AND** scripted delivery on another `FakeWebSocketPort` instance SHALL NOT reach this connection's callbacks
