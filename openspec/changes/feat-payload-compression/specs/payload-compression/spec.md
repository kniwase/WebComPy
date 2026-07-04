## ADDED Requirements

### Requirement: serialize_payload shall support optional gzip compression

`serialize_payload(payload, compression_threshold: int | None = 1024)` SHALL compress the serialized JSON when its byte length exceeds `compression_threshold`. Compression SHALL use `zlib.compress()` (stdlib). The compressed bytes SHALL be base64-encoded via `base64.b64encode()` and wrapped in an envelope: `{"__webcompy_compressed__": true, "__webcompy_transfer_version__": <version>, "data": "<base64>"}`. When the serialized JSON does not exceed the threshold, or when `compression_threshold` is `None` or `0`, the payload SHALL be stored uncompressed (no envelope).

#### Scenario: Payload above threshold is compressed
- **WHEN** `serialize_payload(payload, compression_threshold=1024)` is called
- **AND** the serialized JSON exceeds 1024 bytes
- **THEN** the output SHALL be the compression envelope with `"__webcompy_compressed__": true`
- **AND** the `"data"` field SHALL contain the base64-encoded gzip-compressed JSON

#### Scenario: Payload below threshold is not compressed
- **WHEN** `serialize_payload(payload, compression_threshold=1024)` is called
- **AND** the serialized JSON is 500 bytes
- **THEN** the output SHALL be the uncompressed JSON (no envelope)
- **AND** no `"__webcompy_compressed__"` key SHALL be present

#### Scenario: Compression disabled by threshold=None
- **WHEN** `serialize_payload(payload, compression_threshold=None)` is called
- **THEN** the output SHALL be uncompressed regardless of payload size

#### Scenario: Compression disabled by threshold=0
- **WHEN** `serialize_payload(payload, compression_threshold=0)` is called
- **THEN** the output SHALL be uncompressed regardless of payload size

### Requirement: deserialize_payload shall detect and decompress compressed payloads

`deserialize_payload(text)` SHALL check for the presence of `"__webcompy_compressed__"` in the parsed JSON. If present and `true`, the function SHALL base64-decode the `"data"` field, gzip-decompress it via `zlib.decompress()`, and JSON-parse the result. If the flag is absent or `false`, the function SHALL process the JSON as before (uncompressed path).

#### Scenario: Deserializing a compressed payload
- **WHEN** `deserialize_payload(text)` receives a JSON string containing `"__webcompy_compressed__": true`
- **THEN** the `"data"` field SHALL be base64-decoded
- **AND** the result SHALL be gzip-decompressed via `zlib.decompress()`
- **AND** the decompressed string SHALL be JSON-parsed
- **AND** the resulting `TransferPayload` SHALL be returned

#### Scenario: Deserializing an uncompressed payload (backward compatibility)
- **WHEN** `deserialize_payload(text)` receives a JSON string without `"__webcompy_compressed__"`
- **THEN** the JSON SHALL be processed as before (uncompressed path)
- **AND** the behavior SHALL be identical to the pre-compression implementation

### Requirement: Compression shall use only stdlib modules

The compression and decompression logic SHALL use only `zlib`, `base64`, and `json` from the Python standard library. No third-party compression libraries SHALL be required. This ensures the codec works in both CPython (server) and PyScript/Emscripten (browser) environments without external dependencies.

#### Scenario: No third-party compression dependency
- **WHEN** the `webcompy.hydration._payload` module is imported
- **THEN** only stdlib modules (`zlib`, `base64`, `json`) SHALL be used for compression
- **AND** no `import brotli` or similar third-party imports SHALL exist

### Requirement: The compression envelope shall preserve the transfer version

The compression envelope SHALL include the `"__webcompy_transfer_version__"` field at the top level (alongside `"__webcompy_compressed__"` and `"data"`). This field is **informational/diagnostic** — it allows version inspection without decompression. The **authoritative** version is the one inside the decompressed JSON. If the two disagree, the inner (decompressed) version SHALL take precedence and the envelope version SHALL be treated as a stale cache. The serializer SHALL keep both in sync at serialization time.

#### Scenario: Envelope contains version field
- **WHEN** a compressed payload is produced
- **THEN** the envelope SHALL contain `"__webcompy_transfer_version__"` with the correct version number
- **AND** after decompression, the inner JSON SHALL also contain the version (for consistency)

#### Scenario: Inner version is authoritative on mismatch
- **WHEN** the envelope's `"__webcompy_transfer_version__"` differs from the decompressed JSON's version
- **THEN** the inner (decompressed) version SHALL be treated as authoritative
- **AND** the envelope version SHALL be treated as informational only
