# Lock File — Delta: feat-pyscript-local-serving

## ADDED Requirements

### Requirement: The lock file shall record the runtime serving mode
`webcompy-lock.json` SHALL include a `runtime_serving` field indicating whether PyScript/Pyodide runtime assets are served from CDN or locally.

#### Scenario: Lock file with local runtime serving
- **WHEN** a lock file is generated with `runtime_serving="local"`
- **THEN** the lock file SHALL contain `"runtime_serving": "local"`
- **AND** the lock file SHALL include a `runtime_assets` section

#### Scenario: Lock file with CDN runtime serving (default)
- **WHEN** a lock file is generated with `runtime_serving="cdn"` (default)
- **THEN** the lock file SHALL contain `"runtime_serving": "cdn"`
- **AND** the `runtime_assets` section SHALL NOT be present

### Requirement: The lock file shall include runtime asset metadata when runtime_serving is local
When `runtime_serving="local"`, `webcompy-lock.json` SHALL include a `runtime_assets` section recording the download URLs and SHA256 hashes of PyScript and Pyodide runtime files.

#### Scenario: Runtime assets section
- **WHEN** a lock file is generated with `runtime_serving="local"`
- **THEN** the `runtime_assets` section SHALL contain entries for `core_js`, `core_css`, `pyodide_mjs`, `pyodide_asm_wasm`, `pyodide_asm_js`, and `python_stdlib_zip`
- **AND** each entry SHALL include the download `url` and `sha256` hash
- **AND** the `pyodide_lock_json` entry SHALL include the download `url` and `sha256` hash

#### Scenario: Runtime assets absent in CDN mode
- **WHEN** a lock file is generated with `runtime_serving="cdn"`
- **THEN** the `runtime_assets` section SHALL NOT be present
