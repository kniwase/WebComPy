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
When `runtime_serving="local"`, `webcompy-lock.json` SHALL include a `runtime_assets` section recording the download URLs of PyScript and Pyodide runtime files. SHA256 hashes are populated after the first build: `webcompy lock` records URLs only (with `sha256: null`), and the first `webcompy start` or `webcompy generate` computes and writes SHA256 hashes to the lock file. Subsequent builds verify downloaded files against these recorded hashes.

#### Scenario: Runtime assets section after lock generation
- **WHEN** a lock file is generated with `webcompy lock` and `runtime_serving="local"`
- **THEN** the `runtime_assets` section SHALL contain entries for `core.js`, `core.css`, `pyodide.mjs`, `pyodide.asm.wasm`, `pyodide.asm.js`, `python_stdlib.zip`, and `pyodide-lock.json`
- **AND** each entry SHALL include the download `url`
- **AND** each entry's `sha256` SHALL be `null` (not yet computed)

#### Scenario: Runtime assets section after first build
- **WHEN** a build (`webcompy start` or `webcompy generate`) runs with `runtime_serving="local"` and downloads runtime assets
- **THEN** each `runtime_assets` entry SHALL be updated with the computed `sha256` hash
- **AND** the lock file SHALL be re-saved with the computed hashes

#### Scenario: SHA256 verification on subsequent builds
- **WHEN** a build runs with `runtime_serving="local"` and the lock file already contains `runtime_assets` with `sha256` hashes
- **THEN** each downloaded file's SHA256 SHALL be verified against the recorded hash
- **AND** a mismatch SHALL raise a `RuntimeDownloadError`

#### Scenario: Runtime assets absent in CDN mode
- **WHEN** a lock file is generated with `runtime_serving="cdn"`
- **THEN** the `runtime_assets` section SHALL NOT be present
