## ADDED Requirements

### Requirement: HttpClient form requests shall be routed through FetchPort

`HttpClient` requests carrying `form_data` SHALL be encoded as `multipart/form-data` bodies (RFC 7578 simple name/value fields, values of type `str | bytes`) and SHALL be dispatched through the injected `FetchPort` exactly like JSON and raw-body requests. The client SHALL set the request `Content-Type` to the encoded multipart media type including its boundary unless the caller explicitly provides a `Content-Type` header. The browser runtime module for `HttpClient` SHALL NOT access the raw browser object or an FFI proxy for `form_data` requests. The DOM-node form path (`form_element`) remains browser-only and SHALL raise a descriptive error when no browser environment is available.

#### Scenario: Form submission works during SSR/SSG via self-site fetch
- **WHEN** a component running during server-side rendering calls `HttpClient.post("/api/submit", form_data={"a": "1"})`
- **THEN** the request SHALL be dispatched through the injected server-side fetch port as a multipart body
- **AND** the self-site target SHALL receive a well-formed `multipart/form-data` payload

#### Scenario: Form submissions are fakable in unit tests
- **WHEN** a test injects a fake fetch port and calls `HttpClient.post(url, form_data={"name": "value", "blob": b"bytes"})`
- **THEN** the fake port SHALL observe the request with a multipart-encoded bytes body and the corresponding `Content-Type` header

#### Scenario: Explicit Content-Type wins
- **WHEN** `HttpClient.post(url, headers={"Content-Type": "application/x-custom"}, form_data={"a": "1"})` is called
- **THEN** the outgoing request SHALL keep the caller-supplied `Content-Type` header

#### Scenario: Non-browser use of form_element fails descriptively
- **WHEN** `HttpClient.request(..., form_element=ref)` runs outside a browser environment
- **THEN** it SHALL raise an exception whose message explains that `form_element` requires a browser environment
