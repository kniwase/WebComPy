## MODIFIED Requirements

### Requirement: `TransferPayload` SHALL include a `resources` field for embedded resource bytes

`TransferPayload` SHALL add a fourth field in addition to `fetches`, `async_results`, and `signals`:

```python
resources: dict[str, str] = field(default_factory=dict)
```

where each key is a package-relative POSIX path (e.g., `templates/card.html`) and each value is the base64-encoded raw bytes of the resource. `__webcompy_transfer_version__` SHALL be bumped from `2` to `3` to signal the schema extension.

`deserialize_payload()` SHALL accept version 3 payloads and continue to accept versions 1 and 2 for backward compatibility. A v1 or v2 payload is treated as having an empty `resources` dict.

#### Scenario: V3 payload with resources serialized
- **WHEN** `serialize_payload()` is called with a `TransferPayload` containing `resources={"templates/card.html": base64(...)}`
- **THEN** the JSON output SHALL include `"__webcompy_transfer_version__": 3`
- **AND** the `"resources"` key SHALL be present with the base64 strings preserved

#### Scenario: V3 payload deserialized
- **WHEN** `deserialize_payload()` receives a v3 JSON string
- **THEN** the resulting `TransferPayload.resources` SHALL be a dict mapping each path to its base64-encoded content

#### Scenario: V1 payload still accepted (backward compat)
- **WHEN** `deserialize_payload()` receives a v1 JSON string (no `resources` key)
- **THEN** the resulting `TransferPayload.resources` SHALL be an empty dict `{}`
- **AND** no error SHALL be raised

#### Scenario: V2 payload still accepted (backward compat)
- **WHEN** `deserialize_payload()` receives a v2 JSON string (no `resources` key)
- **THEN** the resulting `TransferPayload.resources` SHALL be an empty dict `{}`
- **AND** the existing `signals` and `async_results` fields SHALL be populated identically

#### Scenario: Unknown version rejected
- **WHEN** `deserialize_payload()` receives a JSON string with `__webcompy_transfer_version__` outside `{1, 2, 3}`
- **THEN** the return value SHALL be `None`

### Requirement: A `RESOURCE_DATA_KEY` DI key exposes the embedded resource bytes to the browser port

`webcompy/di/_keys.py` SHALL define `RESOURCE_DATA_KEY = InjectKey[dict[str, str]]("webcompy-resource-data")` (mirroring the existing `HYDRATION_DATA_KEY` and `HYDRATION_SIGNAL_DATA_KEY` pattern). The value SHALL be the decoded `payload.resources` dict (base64 strings keyed by package-relative path).

#### Scenario: RESOURCE_DATA_KEY importable
- **WHEN** a developer writes `from webcompy.di import RESOURCE_DATA_KEY`
- **THEN** the import SHALL succeed
- **AND** the key SHALL be usable as the first argument to `inject()`

#### Scenario: Browser port consumes RESOURCE_DATA_KEY during hydration
- **WHEN** `BrowserResourcePort().load_text("templates/card.html")` is called and `RESOURCE_DATA_KEY` is provided in the DI scope with a matching entry
- **THEN** the base64-decoded content SHALL be returned
- **AND** no HTTP fetch SHALL be issued

### Requirement: SSR SHALL populate `payload.resources` from each `RenderContext`'s `ServerResourcePort`

During SSR/SSG, after component rendering completes for a request, `ServerRenderContext` SHALL collect the recorded resources from every active `ServerResourcePort` (via `port.get_recorded_resources()`) and populate `TransferPayload.resources` with the path → bytes mapping. The codec pipeline SHALL base64-encode the bytes prior to JSON serialization.

#### Scenario: Loaded resource appears in hydration payload
- **WHEN** an async component in an SSR'd page calls `await load_text("templates/card.html")`
- **AND** the resource file exists
- **THEN** the resulting `__webcompy_data__` script SHALL include `"templates/card.html"` in the `resources` dict
- **AND** the value SHALL be the base64 of the file's bytes

#### Scenario: Failed load does not appear in payload
- **WHEN** a component calls `await load_text("missing.html")` and the load raises
- **THEN** the `resources` dict SHALL NOT contain `"missing.html"` after SSR

#### Scenario: Same resource loaded twice appears once in payload
- **WHEN** two components call `await load_text("templates/card.html")` during the same SSR pass
- **THEN** the `resources` dict SHALL contain a single entry for `"templates/card.html"` with the latest content

### Requirement: Payload compression SHALL apply to the `resources` field

The existing `compression_threshold` mechanism (gzip envelope triggered above the size threshold, via the `__webcompy_compressed__` flag) SHALL apply to v3 payloads including the new `resources` field. No special-case compression logic SHALL be added for `resources` specifically.

#### Scenario: Large resources trigger compression
- **WHEN** the unencoded payload size exceeds the configured `compression_threshold`
- **THEN** the serialized output SHALL be gzipped and base64-encoded with the `__webcompy_compressed__` envelope
- **AND** the `resources` field SHALL be included in the gzipped output
