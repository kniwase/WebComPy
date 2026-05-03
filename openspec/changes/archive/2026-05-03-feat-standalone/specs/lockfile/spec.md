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

### Requirement: The lock file shall reflect the current standalone mode when regenerated
When switching between standalone and non-standalone modes, regenerating the lock file SHALL update all relevant fields to reflect the new configuration. The lock file is not automatically regenerated; the developer must run `webcompy lock` (or a generate/start command) to update it.

#### Scenario: Regenerating lock file after switching from standalone to non-standalone
- **WHEN** a lock file was generated with `standalone=True` and is regenerated with `standalone=False`
- **THEN** `standalone` SHALL be `false`
- **AND** `wasm_serving` SHALL be `"cdn"`
- **AND** `runtime_serving` SHALL be `"cdn"`
- **AND** the `runtime_assets` section SHALL be omitted (no longer needed in CDN mode)

#### Scenario: Regenerating lock file after switching from non-standalone to standalone
- **WHEN** a lock file was generated with `standalone=False` and is regenerated with `standalone=True`
- **THEN** `standalone` SHALL be `true`
- **AND** `wasm_serving` SHALL be `"local"`
- **AND** `runtime_serving` SHALL be `"local"`
- **AND** the `runtime_assets` section SHALL be populated with URLs for all runtime assets
