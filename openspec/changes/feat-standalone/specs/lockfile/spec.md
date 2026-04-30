# Lock File — Delta: feat-standalone

## ADDED Requirements

### Requirement: The lock file shall record the standalone flag
When `standalone=True` is set, `webcompy-lock.json` SHALL include a `"standalone": true` field for informational purposes. The actual asset metadata is recorded in the `runtime_assets` section (from `feat-pyscript-local-serving`) and `wasm_packages` entries. No separate `standalone_assets` section is needed.

#### Scenario: Lock file with standalone mode
- **WHEN** a lock file is generated with `standalone=True`
- **THEN** the lock file SHALL contain `"standalone": true`
- **AND** `wasm_serving` SHALL be `"local"`
- **AND** `runtime_serving` SHALL be `"local"`
- **AND** the `runtime_assets` section SHALL be populated (as defined by `feat-pyscript-local-serving`)

#### Scenario: Lock file without standalone mode
- **WHEN** a lock file is generated without standalone mode
- **THEN** the `standalone` field SHALL be `false`
