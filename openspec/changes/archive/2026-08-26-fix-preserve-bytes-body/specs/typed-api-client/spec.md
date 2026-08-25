## ADDED Requirements

### Requirement: HttpClient shall preserve raw body and header fidelity through FetchPort

`HttpClient.request` SHALL pass `body_data` to the injected `FetchPort` with its original type preserved — a `str` value SHALL arrive as `str`, a `bytes` value SHALL arrive as `bytes` — without decoding, re-encoding, or other transformation. It SHALL pass request header names and values to `FetchPort` without percent-encoding, so a caller-supplied `Content-Type` containing `;` or `=` (for example `multipart/form-data; boundary=...` or `application/json; charset=utf-8`) SHALL arrive at the transport unchanged. Auto-generated `Content-Type` values (`application/json` for `json` bodies, `multipart/form-data; boundary=...` for `form_data`) SHALL also be sent without percent-encoding.

#### Scenario: Binary body_data is preserved as bytes

- **WHEN** `await HttpClient.post("/api/blob", body_data=b"\x00\x01\xff")` is called with a `FakeFetchPort` injected
- **THEN** the port SHALL observe `body == b"\x00\x01\xff"` (exact bytes, no decode)

#### Scenario: Text body_data is preserved as str

- **WHEN** `await HttpClient.post("/api/text", body_data="hello")` is called
- **THEN** the port SHALL observe `body == "hello"` (exact str)

#### Scenario: Non-UTF-8 bytes do not raise

- **WHEN** `await HttpClient.post("/api/blob", body_data=b"\xff\xfe")` is called with bytes that are not valid UTF-8
- **THEN** the request SHALL be dispatched without raising `UnicodeDecodeError` or `UnicodeError`

#### Scenario: Caller Content-Type with semicolon is not mangled

- **WHEN** `await HttpClient.post("/api/submit", headers={"Content-Type": "multipart/form-data; boundary=custom"}, form_data={"a": "1"})` is called
- **THEN** the port SHALL observe `headers["Content-Type"] == "multipart/form-data; boundary=custom"` (no `%3B` or `%20`)

#### Scenario: Charset Content-Type with semicolon is not mangled

- **WHEN** `await HttpClient.post("/api/json", headers={"Content-Type": "application/json; charset=utf-8"}, json={"a": 1})` is called
- **THEN** the port SHALL observe `headers["Content-Type"] == "application/json; charset=utf-8"` (explicit caller value wins and is not percent-encoded)
