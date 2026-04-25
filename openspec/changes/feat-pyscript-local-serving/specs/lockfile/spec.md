# Lock File — Delta: feat-pyscript-local-serving

## ADDED Requirements

### Requirement: The lock file shall include local-serving asset information
When `runtime_serving="local"` is set, `webcompy-lock.json` SHALL include a `runtime_assets` section recording the URLs and SHA256 hashes of downloaded PyScript and Pyodide runtime files (not dependency packages — those are handled by `feat-deps-local-serving` and `feat-wasm-local-serving`).

#### Scenario: Lock file with local-serving assets
- **WHEN** a lock file is generated with `runtime_serving="local"`
- **THEN** the `runtime_assets` section SHALL contain entries for `core_js`, `core_css`, `pyodide_mjs`, `pyodide_asm_wasm`, `pyodide_asm_js`, and `python_stdlib_zip`
- **AND** each entry SHALL include the download `url` and `sha256` hash

#### Scenario: Lock file without local-serving assets
- **WHEN** a lock file is generated without runtime-local mode
- **THEN** the `runtime_assets` section SHALL be an empty object `{}`