## MODIFIED Requirements

### Requirement: The lock file shall use v2 schema with wasm_packages and pure_python_packages
The lock file SHALL use schema version 2, which replaces `pyodide_packages` with `wasm_packages` and `bundled_packages` with `pure_python_packages`. Version 1 lock files SHALL be treated as invalid (returning `None` from `load_lockfile()`), triggering full regeneration. `webcompy-lock.json` SHALL be a JSON file placed in the app package directory (next to `webcompy_config.py`) that records WASM package versions, pure-Python package versions and CDN metadata, and the Pyodide/PyScript versions used. The lock file SHALL be version-controlled (like `uv.lock` or `poetry.lock`). CDN-available pure-Python package entries include `in_pyodide_cdn`, `pyodide_file_name`, and `pyodide_sha256` fields. Additional keys (e.g., `standalone_assets`) may be added by other changes. Population of `wasm_packages` and `pure_python_packages` SHALL be determined by `PackageKind` from `classify_dependencies()`: `PackageKind.WASM` entries go to `wasm_packages`, `PackageKind.CDN_PURE_PYTHON` and `PackageKind.LOCAL_PURE_PYTHON` entries go to `pure_python_packages`.

#### Scenario: Lock file generated on first run
- **WHEN** a developer runs `webcompy start` or `webcompy generate` without an existing lock file
- **THEN** the lock file SHALL be automatically generated and saved
- **AND** the developer SHOULD commit the lock file to version control

#### Scenario: v2 lock file schema
- **WHEN** a lock file is generated
- **THEN** it SHALL contain `version: 2`, `pyodide_version`, `pyscript_version`, `wasm_packages`, and `pure_python_packages`

#### Scenario: v1 lock file rejection
- **WHEN** `load_lockfile()` encounters a lock file with `version: 1`
- **THEN** it SHALL return `None`
- **AND** the build system SHALL regenerate the lock file

#### Scenario: WASM package classified via PackageKind
- **WHEN** `classify_dependencies()` classifies `numpy` as `PackageKind.WASM`
- **THEN** `numpy` SHALL be recorded in `wasm_packages` with `version`, `file_name`, and `source`

#### Scenario: CDN pure-Python package classified via PackageKind
- **WHEN** `classify_dependencies()` classifies `httpx` as `PackageKind.CDN_PURE_PYTHON`
- **THEN** `httpx` SHALL be recorded in `pure_python_packages` with `in_pyodide_cdn=True`, `pyodide_file_name`, and `pyodide_sha256`

#### Scenario: Local pure-Python package classified via PackageKind
- **WHEN** `classify_dependencies()` classifies `flask` as `PackageKind.LOCAL_PURE_PYTHON`
- **THEN** `flask` SHALL be recorded in `pure_python_packages` with `in_pyodide_cdn=False`, `pyodide_file_name=None`, and `pyodide_sha256=None`