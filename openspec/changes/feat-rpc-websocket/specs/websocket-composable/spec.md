# WebSocket Composable Specification (delta)

## ADDED Requirements

### Requirement: The WebSocket handle shall support force-closing with a non-normal close code

The WebSocket handle returned by `use_websocket` SHALL expose `force_close(code, reason)` that records a synthetic `CloseInfo(code, reason, was_clean=False)`, closes the underlying socket, and keeps the connection alive in the registry, so the reconnect loop engages (i.e., the state SHALL transition to `RECONNECTING` and later back to `OPEN` on recovery). Calling `force_close` on a handle whose connection is already closed or terminated SHALL be a no-op. After `force_close`, stale lifecycle events from the old socket (e.g., the browser's own close event with code 1000) SHALL be ignored. The typed handle SHALL forward `force_close` to the underlying raw handle.

#### Scenario: Force close engages the reconnect loop

- **WHEN** `handle.force_close(4000, "heartbeat timeout")` is called on an open connection
- **THEN** `.last_close` SHALL report `CloseInfo(4000, ..., was_clean=False)`
- **AND** `.state` SHALL transition through `RECONNECTING` back to `OPEN` when a new connection is established

#### Scenario: Force close is a no-op on a closed connection

- **WHEN** `handle.force_close(...)` is called after the connection has been closed or terminated
- **THEN** no transition SHALL occur and no error SHALL be raised

#### Scenario: Stale close events after force close are ignored

- **WHEN** the underlying socket fires its own close event (code `1000`) after `force_close` has been called
- **THEN** the connection SHALL NOT be terminated and the reconnect loop SHALL continue

#### Scenario: Force close on a non-reconnecting connection terminates it

- **WHEN** `force_close(...)` is called on a connection with `reconnect=False` or with `reconnect_max_attempts` already exhausted
- **THEN** the connection SHALL transition to `CLOSED`
- **AND** no retry SHALL be scheduled