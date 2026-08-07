# Delta Spec: typed-api-client

## ADDED Requirements

### Requirement: Typed deserialization shall consume transfer metadata when present
The `response_type` path of `HttpClient` and `from_json` SHALL recognize transfer metadata in both wire placements defined by `typed-response`: the `__webcompy_transfer_meta__` body key and the `X-WebComPy-Transfer-Meta` response header. When both are present (non-conforming servers), the body key SHALL take precedence. Metadata-driven restoration SHALL apply at the recorded paths and SHALL take precedence over schema-driven coercion for those exact values (restoring types such as `bytes`, `set`, `tuple`, and `Decimal` that annotations alone cannot identify). When no metadata is present, behavior SHALL remain purely schema-driven. `from_json` SHALL accept an optional `meta` parameter for standalone use.

#### Scenario: Bytes restoration via metadata
- **WHEN** a response body contains base64 text at a path recorded in metadata with type tag `bytes`
- **AND** the target field is annotated `bytes`
- **THEN** the reconstructed object SHALL contain the decoded `bytes` value

#### Scenario: Set restoration via metadata
- **WHEN** a JSON array is recorded in metadata with type tag `set` for a field annotated `set[str]`
- **THEN** the reconstructed field SHALL be a Python `set`, not a `list`

#### Scenario: Absent metadata behaves exactly as schema-driven
- **WHEN** a response carries neither `__webcompy_transfer_meta__` nor `X-WebComPy-Transfer-Meta`
- **THEN** deserialization SHALL behave exactly as specified by the schema-driven requirements

#### Scenario: Body key takes precedence over header
- **WHEN** both `__webcompy_transfer_meta__` and `X-WebComPy-Transfer-Meta` are present
- **THEN** the body key metadata SHALL be used
