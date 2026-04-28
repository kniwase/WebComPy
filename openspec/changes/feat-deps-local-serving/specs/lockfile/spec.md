# Lock File — Delta: feat-deps-local-serving

## MODIFIED Requirements

### Requirement: The lock file shall use v2 schema with wasm_packages and pure_python_packages
The lock file SHALL use schema version 2, which replaces `pyodide_packages` with `wasm_packages` and `bundled_packages` with `pure_python_packages`. Version 1 lock files SHALL be treated as invalid (returning `None` from `load_lockfile()`), triggering full regeneration.

#### Scenario: v2 lock file schema
- **WHEN** a lock file is generated
- **THEN** it SHALL contain `version: 2`, `pyodide_version`, `pyscript_version`, `wasm_packages`, and `pure_python_packages`

#### Scenario: v1 lock file rejection
- **WHEN** `load_lockfile()` encounters a lock file with `version: 1`
- **THEN** it SHALL return `None`
- **AND** the build system SHALL regenerate the lock file

### Requirement: wasm_packages shall contain only WASM packages
`wasm_packages` SHALL contain only WASM packages that must be loaded from the Pyodide CDN by name via `py-config.packages`. Pure-Python packages available in the Pyodide CDN SHALL NOT appear in `wasm_packages`.

#### Scenario: WASM package entry in v2 lock file
- **WHEN** a dependency `numpy` is a WASM package
- **THEN** it SHALL be recorded in `wasm_packages` with `version`, `file_name`, and `source`

#### Scenario: Pure-Python CDN package not in wasm_packages
- **WHEN** a dependency `httpx` is a pure-Python package in the Pyodide CDN
- **THEN** it SHALL NOT appear in `wasm_packages`
- **AND** it SHALL appear in `pure_python_packages`

### Requirement: pure_python_packages shall contain all pure-Python packages with CDN metadata
`pure_python_packages` SHALL contain all pure-Python dependencies regardless of CDN availability. Entries for CDN-available packages SHALL include `in_pyodide_cdn: true` with `pyodide_file_name` and `pyodide_sha256` for download. Entries for local-only packages SHALL have `in_pyodide_cdn: false`.

#### Scenario: CDN-available pure-Python package entry
- **WHEN** a pure-Python package `httpx` is available in the Pyodide CDN
- **THEN** the entry SHALL include `in_pyodide_cdn: true`, `pyodide_file_name: "httpx-0.28.1-py3-none-any.whl"`, and `pyodide_sha256`
- **AND** `serve_all_deps=True` SHALL cause this package to be downloaded at build time

#### Scenario: Local-only pure-Python package entry
- **WHEN** a pure-Python package `flask` is NOT available in the Pyodide CDN
- **THEN** the entry SHALL include `in_pyodide_cdn: false`
- **AND** it SHALL NOT have `pyodide_file_name` or `pyodide_sha256`
- **AND** this package SHALL always be bundled from local installation

#### Scenario: Pure-Python CDN package is bundled when serve_all_deps=True
- **WHEN** `serve_all_deps=True` and a pure-Python package has `in_pyodide_cdn: true`
- **THEN** the build system SHALL download the wheel, verify SHA256, extract, and bundle it

#### Scenario: Pure-Python CDN package is loaded from CDN when serve_all_deps=False
- **WHEN** `serve_all_deps=False` and a pure-Python package has `in_pyodide_cdn: true`
- **THEN** the package name SHALL be included in `py-config.packages` for CDN loading
- **AND** the package SHALL NOT be bundled

## ADDED Requirements

### Requirement: The lock file shall support querying CDN-available pure-Python package names
`get_cdn_pure_python_package_names(lockfile)` SHALL return the names of pure-Python packages with `in_pyodide_cdn=True`. This is used when `serve_all_deps=False` to generate the `py-config.packages` list.

#### Scenario: Querying CDN pure-Python names
- **WHEN** a lock file contains `pure_python_packages` with `httpx (in_pyodide_cdn=true)` and `flask (in_pyodide_cdn=false)`
- **THEN** `get_cdn_pure_python_package_names()` SHALL return `["httpx"]`

### Requirement: get_bundled_deps shall consider serve_all_deps
`get_bundled_deps(lockfile, serve_all_deps=True)` SHALL return all pure-Python packages when `serve_all_deps=True`, and only local-only pure-Python packages when `serve_all_deps=False`.

#### Scenario: get_bundled_deps with serve_all_deps=True
- **WHEN** `serve_all_deps=True`
- **THEN** `get_bundled_deps()` SHALL return all `pure_python_packages` entries that have local `pkg_dir` available
- **AND** CDN packages to be downloaded are handled separately via the download pipeline

#### Scenario: get_bundled_deps with serve_all_deps=False
- **WHEN** `serve_all_deps=False`
- **THEN** `get_bundled_deps()` SHALL return only `pure_python_packages` entries with `in_pyodide_cdn=False`