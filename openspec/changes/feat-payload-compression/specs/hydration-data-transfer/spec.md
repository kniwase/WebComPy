## ADDED Requirements

### Requirement: serialize_payload and deserialize_payload shall support compressed payloads

`serialize_payload()` SHALL accept an optional `compression_threshold: int | None` parameter. When the serialized payload exceeds the threshold, it SHALL be gzip-compressed via `zlib`, base64-encoded, and wrapped in a `{"__webcompy_compressed__": true, ...}` envelope. `deserialize_payload()` SHALL detect the `__webcompy_compressed__` flag and decompress accordingly. Uncompressed payloads (without the flag) SHALL be processed as before, ensuring backward compatibility.

#### Scenario: Round-trip compressed payload
- **WHEN** a `TransferPayload` is serialized with compression enabled
- **AND** the serialized size exceeds the threshold
- **AND** the compressed output is passed to `deserialize_payload()`
- **THEN** the resulting `TransferPayload` SHALL be equal to the original (all fields preserved)

#### Scenario: Uncompressed payload backward compatibility
- **WHEN** `deserialize_payload()` receives a payload without `__webcompy_compressed__`
- **THEN** the payload SHALL be processed as uncompressed JSON
- **AND** the behavior SHALL be identical to the pre-compression implementation
