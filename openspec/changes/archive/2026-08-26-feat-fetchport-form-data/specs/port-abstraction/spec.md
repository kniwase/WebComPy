## ADDED Requirements

### Requirement: FetchPort shall accept text and binary request bodies

`FetchPort.fetch()` and `FetchPort.stream()` SHALL accept a `body` parameter of type `str | bytes | None`. Implementations SHALL pass the body to their underlying transport unchanged, regardless of whether it is text or bytes. Port implementations that cache responses by request key SHALL derive deterministic cache keys from bytes bodies (e.g., via a content hash) rather than relying on object representation.

#### Scenario: Binary body reaches the transport unchanged
- **WHEN** `fetch_port.fetch(url, method="POST", headers={"Content-Type": "multipart/form-data; boundary=abc123"}, body=b"--abc123\r\n...")` is called
- **THEN** the underlying transport SHALL receive the exact bytes passed as `body`

#### Scenario: Text bodies continue to work
- **WHEN** `fetch_port.fetch(url, method="POST", body="hello")` is called
- **THEN** the behavior SHALL be identical to before this capability existed

#### Scenario: Cache keys for bytes bodies are deterministic
- **WHEN** the same POST request with identical bytes body is issued twice against an implementation with a response cache
- **THEN** both requests SHALL resolve to the same cache entry
