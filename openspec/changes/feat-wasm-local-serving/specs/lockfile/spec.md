# Lock File — Delta: feat-wasm-local-serving

## ADDED Requirements

### Requirement: The lock file shall record the WASM serving mode
`webcompy-lock.json` SHALL include a `wasm_serving` field indicating whether WASM packages are served from CDN or locally.

#### Scenario: Lock file with local WASM serving
- **WHEN** a lock file is generated with `wasm_serving="local"`
- **THEN** the lock file SHALL contain `"wasm_serving": "local"`
- **AND** WASM packages in `pyodide_packages` SHALL include their download URLs for verification

#### Scenario: Lock file with CDN WASM serving (default)
- **WHEN** a lock file is generated with `wasm_serving="cdn"` (default)
- **THEN** the lock file SHALL contain `"wasm_serving": "cdn"` or omit the field