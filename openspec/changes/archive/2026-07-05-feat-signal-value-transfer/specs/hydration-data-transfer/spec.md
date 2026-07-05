## MODIFIED Requirements

### Requirement: TransferPayload shall include fetches, async_results, and signals

`TransferPayload` SHALL contain `__webcompy_transfer_version__: int`, `fetches: dict[str, TransferFetchEntry]`, `async_results: dict[str, TransferAsyncResultEntry]`, and `signals: dict[str, dict[str, Any]]`. The `signals` field maps component ID to a dict of `{attr_name: encoded_value}` where encoded values are produced by `encode()` from `webcompy.hydration._codec`. The supported version SHALL be `2`. The `deserialize_payload()` function SHALL accept version 1 payloads (treating a missing `signals` section as empty) and version 2 payloads.

#### Scenario: Serializing a version 2 payload
- **WHEN** `serialize_payload()` is called with a `TransferPayload` containing signals
- **THEN** the JSON output SHALL include `"__webcompy_transfer_version__": 2`
- **AND** the `"signals"` key SHALL be present in the output

#### Scenario: Deserializing a version 2 payload
- **WHEN** `deserialize_payload()` receives a version 2 JSON string
- **THEN** the resulting `TransferPayload` SHALL have the `signals` dict populated from the JSON

#### Scenario: Deserializing a version 1 payload (backward compatibility)
- **WHEN** `deserialize_payload()` receives a version 1 JSON string (no `signals` key)
- **THEN** the resulting `TransferPayload.signals` SHALL be an empty dict `{}`
- **AND** no error SHALL be raised

### Requirement: collect_transfer_data shall collect fetches, async_results, and signals

`collect_transfer_data(root)` SHALL traverse the component tree and populate three sections of the `TransferPayload`: `fetches` (from `FetchPort.get_transfer_data()`), `async_results` (from `Component._async_results`), and `signals` (from `Component.__signal_members__`). Signal values SHALL be encoded via `encode()` from `webcompy.hydration._codec`. Non-serializable Signal values SHALL be dropped with a warning.

#### Scenario: collect_transfer_data gathers all three sections
- **WHEN** `collect_transfer_data(root)` is called after SSR rendering
- **THEN** the returned `TransferPayload` SHALL have `fetches`, `async_results`, and `signals` populated

#### Scenario: collect_transfer_data handles components with no signals
- **WHEN** a component has no `__signal_members__` entries
- **THEN** that component's ID SHALL not appear in the `signals` dict (or shall map to an empty dict)
