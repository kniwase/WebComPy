# CLI — Delta: feat-deps-local-serving

## ADDED Requirements

### Requirement: The CLI shall download pure-Python packages from Pyodide CDN when serve_all_deps is True
When `serve_all_deps=True`, the CLI SHALL download pure-Python package wheels from the Pyodide CDN, verify their SHA256 hashes against the lock file, cache them locally, extract them, and bundle them into the app wheel.

#### Scenario: Downloading and bundling CDN packages
- **WHEN** a developer runs `python -m webcompy start --dev` with `serve_all_deps=True`
- **AND** the lock file contains pure-Python packages with `in_pyodide_cdn=True`
- **THEN** those packages SHALL be downloaded from the Pyodide CDN
- **AND** their SHA256 hashes SHALL be verified against the lock file
- **AND** the wheels SHALL be extracted and bundled into the app wheel
- **AND** downloaded wheels SHALL be cached at `~/.cache/webcompy/pyodide-packages/{pyodide_version}/`

#### Scenario: Cache hit
- **WHEN** a previously downloaded wheel exists in the cache with a matching SHA256 hash
- **THEN** the download SHALL be skipped
- **AND** the cached wheel SHALL be used

#### Scenario: SHA256 verification failure
- **WHEN** a downloaded wheel's SHA256 hash does not match the expected hash from the lock file
- **THEN** the build SHALL fail with a descriptive error
- **AND** the invalid cached file SHALL NOT be used

#### Scenario: Network failure with no cache
- **WHEN** the Pyodide CDN is unreachable and no cached wheel exists
- **THEN** the build SHALL fail with a descriptive error indicating network failure

#### Scenario: Generating static site with serve_all_deps=True
- **WHEN** a developer runs `python -m webcompy generate` with `serve_all_deps=True`
- **THEN** CDN packages SHALL be downloaded, verified, extracted, and bundled into the app wheel in `dist/_webcompy-app-package/`

### Requirement: The CLI shall pass CDN pure-Python package names to HTML when serve_all_deps is False
When `serve_all_deps=False`, pure-Python packages available in the Pyodide CDN SHALL be loaded from the CDN by name. Their package names SHALL appear in `py-config.packages` alongside WASM package names.

#### Scenario: Starting dev server with serve_all_deps=False
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **AND** the lock file contains pure-Python packages with `in_pyodide_cdn=True`
- **THEN** those package names SHALL appear in `py-config.packages`
- **AND** those packages SHALL NOT be bundled into the app wheel

#### Scenario: Generating static site with serve_all_deps=False
- **WHEN** a developer runs `python -m webcompy generate --no-serve-all-deps`
- **THEN** CDN pure-Python package names SHALL appear in the generated HTML `py-config.packages`
- **AND** the app wheel SHALL NOT contain those packages

## MODIFIED Requirements

### Requirement: Dependency classification behavior SHALL depend on serve_all_deps
The behavior of pure-Python packages available in the Pyodide CDN SHALL depend on `AppConfig.serve_all_deps`. When `serve_all_deps=True`, CDN-available pure-Python packages SHALL be downloaded and bundled into the app wheel (replacing the prior behavior where they were neither bundled nor referenced in `py-config.packages`). When `serve_all_deps=False`, CDN-available pure-Python packages SHALL be loaded from the CDN by name via `py-config.packages`.

#### Scenario: serve_all_deps=True (default)
- **WHEN** `serve_all_deps=True` and a pure-Python package is in the Pyodide CDN
- **THEN** it SHALL be downloaded and bundled into the app wheel
- **AND** it SHALL NOT appear in `py-config.packages`

#### Scenario: serve_all_deps=False
- **WHEN** `serve_all_deps=False` and a pure-Python package is in the Pyodide CDN
- **THEN** it SHALL be loaded from the CDN by name via `py-config.packages`
- **AND** it SHALL NOT be bundled into the app wheel

#### Scenario: Pure-Python package not in Pyodide CDN (regardless of serve_all_deps)
- **WHEN** a pure-Python dependency is not in the Pyodide CDN
- **THEN** it SHALL be bundled from local installation into the app wheel
- **AND** it SHALL NOT appear in `py-config.packages`

#### Scenario: WASM package (regardless of serve_all_deps)
- **WHEN** a dependency is a WASM package in the Pyodide CDN
- **THEN** it SHALL be loaded from the CDN by name via `py-config.packages`
- **AND** it SHALL NOT be bundled

### Requirement: The dev server shall serve the application with hot-reload (updated)
The dev server SHALL build a single Python wheel containing the webcompy framework (excluding `webcompy/cli/`), application code, and appropriate pure-Python dependencies based on `serve_all_deps`. When `serve_all_deps=True`, ALL pure-Python dependencies are bundled. When `serve_all_deps=False`, only pure-Python dependencies NOT available from the Pyodide CDN are bundled; CDN-available ones are loaded by name.

#### Scenario: Starting the dev server with serve_all_deps=True
- **WHEN** a developer runs `python -m webcompy start --dev` with `serve_all_deps=True` (default)
- **THEN** the server SHALL build a single wheel containing webcompy (excl. cli), app code, and ALL pure-Python dependencies
- **AND** `py-config.packages` SHALL contain only the app wheel URL and WASM package names
- **AND** CDN-downloaded pure-Python packages SHALL be included in the wheel

#### Scenario: Starting the dev server with serve_all_deps=False
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **THEN** the server SHALL build a single wheel containing webcompy (excl. cli), app code, and locally-bundled dependencies only
- **AND** `py-config.packages` SHALL contain the app wheel URL, WASM package names, AND CDN pure-Python package names