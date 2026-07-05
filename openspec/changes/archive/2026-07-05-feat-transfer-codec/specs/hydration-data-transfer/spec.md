## MODIFIED Requirements

### Requirement: TransferPayload serialization shall use the codec engine

`serialize_payload()` SHALL apply `encode()` from `webcompy.hydration._codec` to `TransferAsyncResultEntry.data` and `TransferFetchEntry.body` before `json.dumps()`. `deserialize_payload()` SHALL apply `decode()` after `json.loads()`. The `__webcompy_transfer_version__` field SHALL remain `1` for payloads without the `signals` section (Signal value transfer, which adds the `signals` section and bumps to version 2, is a separate change). The codec is version-agnostic and works with both v1 and v2 payloads.

Non-serializable values that fail even the codec's extended encoders SHALL be dropped with a warning (consistent with the existing `_try_serialize_value` behavior), preserving the best-effort transfer philosophy.

#### Scenario: AsyncResult data with datetime is transferred correctly
- **WHEN** an `AsyncResult` resolves to a value containing a `datetime` during SSR
- **AND** `serialize_payload()` is called
- **THEN** the datetime SHALL be encoded via the codec as a type-tagged dict `{"__webcompy_type__": "datetime", "__webcompy_value__": "..."}`
- **AND** the browser-side `deserialize_payload()` SHALL reconstruct the `datetime` instance via `decode()`

#### Scenario: AsyncResult data with a dataclass is transferred correctly
- **WHEN** an `AsyncResult` resolves to a dataclass instance during SSR
- **AND** `serialize_payload()` is called
- **THEN** the dataclass SHALL be encoded via the codec with module, class name, and field values
- **AND** the browser-side `deserialize_payload()` SHALL reconstruct the dataclass instance via `importlib.import_module` and `cls(**fields)`

#### Scenario: Non-serializable value failing the codec is dropped
- **WHEN** an `AsyncResult` resolves to a value that the codec cannot encode (e.g., a file handle or socket object)
- **AND** `serialize_payload()` is called
- **THEN** the entry SHALL be dropped from the payload
- **AND** a warning SHALL be logged

#### Scenario: Backward compatibility with plain JSON AsyncResult data
- **WHEN** an `AsyncResult` resolves to a plain JSON-native value (e.g., `{"name": "Alice"}`)
- **AND** `serialize_payload()` is called
- **THEN** the value SHALL pass through the codec unchanged (no type tags added)
- **AND** the encoded output SHALL be identical to the previous `json.dumps` output
