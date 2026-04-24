# Lock File — Delta: feat-standalone-build

## ADDED Requirements

### Requirement: The lock file shall include standalone asset information
When `standalone=True` is set, `webcompy-lock.json` SHALL include a `standalone_assets` section recording the URLs and SHA256 hashes of downloaded PyScript and Pyodide runtime files.

#### Scenario: Lock file with standalone assets
- **WHEN** a lock file is generated with `standalone=True`
- **THEN** the `standalone_assets` section SHALL contain entries for `core_js`, `core_css`, `pyodide_mjs`, `pyodide_asm_wasm`, `pyodide_asm_js`, and `python_stdlib_zip`
- **AND** each entry SHALL include the download `url` and `sha256` hash

#### Scenario: Lock file without standalone assets
- **WHEN** a lock file is generated without standalone mode
- **THEN** the `standalone_assets` section SHALL be an empty object `{}`