# Testing Module Specification (delta)

## ADDED Requirements

### Requirement: webcompy.testing package shall provide a FakeEventSourcePort

`FakeEventSourcePort` SHALL implement `EventSourcePort` with an instance-local registry of open connections (no module-level state). Opening a connection SHALL record the supplied callbacks keyed by `(url, events)` and SHALL return an idempotent cleanup that removes exactly that registration. The fake SHALL expose scripted-delivery helpers (e.g., `emit_event(url, event_type, data, last_event_id)` plus open/error/close lifecycle helpers) that invoke the recorded callbacks for matching registrations, snapshotting the callback list so registrations removed during delivery are not invoked. The fake SHALL NOT construct any native or network object.

#### Scenario: Scripted event delivery reaches subscribers

- **WHEN** `FakeEventSourcePort()` opens a connection for `"/events"` with a message callback
- **AND** `port.emit_event("/events", "message", "hello", "1")` is called
- **THEN** the recorded callback SHALL be invoked with the event data
- **AND** no real network access SHALL occur

#### Scenario: Cleanup is idempotent and removes only its own registration

- **WHEN** two connections are open for the same URL and one cleanup is called twice
- **THEN** no exception SHALL be raised
- **AND** subsequent scripted delivery SHALL reach only the remaining registration

#### Scenario: Registrations are instance-local

- **WHEN** two `FakeEventSourcePort` instances exist
- **THEN** scripted delivery on one SHALL NOT invoke callbacks registered on the other

#### Scenario: Testing render path uses the fake port

- **WHEN** a component using `use_event_source` is rendered through the testing render path (e.g., `TestRenderer.render`)
- **THEN** the composable SHALL open a connection through the provisioned `FakeEventSourcePort`
- **AND** scripted `emit_open` / `emit_event` delivery SHALL reach the composable's handle (e.g., via `.state` and the event iterator)
