# Lock File — Delta: feat-wasm-local-serving

## ADDED Requirements

### Requirement: The lock file shall record the WASM serving mode and local asset metadata
`webcompy-lock.json` SHALL include a `wasm_serving` field indicating whether WASM packages are served from CDN or locally. When `wasm_serving="local"`, WASM package entries in `wasm_packages` SHALL include their Pyodide CDN download URL and SHA256 hash for build-time verification.

#### Scenario: Lock file with local WASM serving
- **WHEN** a lock file is generated with `wasm_serving="local"`
- **THEN** the lock file SHALL contain `"wasm_serving": "local"`
- **AND** each entry in `wasm_packages` SHALL include `file_name` and `sha256` fields for download verification

#### Scenario: Lock file with CDN WASM serving (default)
- **WHEN** a lock file is generated with `wasm_serving="cdn"` (default)
- **THEN** the lock file SHALL contain `"wasm_serving": "cdn"`
- **AND** WASM package entries SHALL include `file_name` for reference but download verification is not required at build time