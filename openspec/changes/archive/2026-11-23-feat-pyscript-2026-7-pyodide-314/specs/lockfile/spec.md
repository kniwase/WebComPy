# Spec Delta

## MODIFIED Requirements

### Requirement: The lock file shall be validated against current dependencies
When loading an existing lock file, the CLI SHALL validate that `AppConfig.dependencies` matches the union of `explicit` entries in `pure_python_packages` and `explicit` entries in `wasm_packages`, AND that the lock file's recorded `pyscript_version` (and resolved `pyodide_version`) matches the active `PYSCRIPT_VERSION`. If dependencies have changed or the recorded runtime versions differ from the active `PYSCRIPT_VERSION`, the lock file SHALL be treated as stale and regenerated automatically. Additionally, the CLI SHALL validate that the local environment provides the packages recorded in the lock file with matching versions.

#### Scenario: Lock file matches dependencies
- **WHEN** the lock file's explicit dependencies match `AppConfig.dependencies`
- **AND** its `pyscript_version` and `pyodide_version` match the active runtime pin
- **THEN** the lock file SHALL be used as-is

#### Scenario: Lock file is stale
- **WHEN** `AppConfig.dependencies` has been modified since the lock file was generated
- **THEN** the lock file SHALL be regenerated automatically

#### Scenario: Lock file has mismatched PyScript or Pyodide version
- **WHEN** an existing lock file records a different `pyscript_version` or `pyodide_version` than the active `PYSCRIPT_VERSION` (for example `2026.3.1` / `0.29.3` when `2026.7.3` / `314.0.3` is pinned)
- **THEN** the lock file SHALL be treated as stale and regenerated automatically for the active `PYSCRIPT_VERSION`

#### Scenario: Pure-Python package missing from local environment
- **WHEN** a package listed in `pure_python_packages` with `in_pyodide_cdn=false` is not found in the local Python environment via `importlib.util.find_spec()`
- **THEN** an error SHALL be reported with the package name, the lock file version, and a suggestion to install it (e.g., `pip install <package>==<version>`)
- **AND** the build SHALL fail

#### Scenario: CDN-available pure-Python package missing locally with serve_all_deps=True
- **WHEN** a package listed in `pure_python_packages` with `in_pyodide_cdn=true` is not found in the local environment
- **AND** `serve_all_deps=True`
- **THEN** a warning SHALL be reported indicating the package will be downloaded from the Pyodide CDN
- **AND** the build SHALL continue

#### Scenario: Pure-Python package version mismatch
- **WHEN** a pure-Python package listed in `pure_python_packages` has version `X.Y.Z` in the lock file, but `importlib.metadata.version()` reports a different version
- **THEN** an error SHALL be reported indicating the version mismatch (lock file version vs. local version)
- **AND** the error SHALL suggest installing the lock file version (e.g., `pip install <package>==X.Y.Z`)
- **AND** the build SHALL fail

#### Scenario: Pure-Python package version unknown locally
- **WHEN** a pure-Python package listed in `pure_python_packages` is found locally via `importlib.util.find_spec()`, but `importlib.metadata.version()` returns `None` (version cannot be determined)
- **THEN** an error SHALL be reported indicating the version could not be determined locally
- **AND** the error SHALL include the lock file version requirement
- **AND** the build SHALL fail

#### Scenario: CDN-available pure-Python package version mismatch
- **WHEN** a pure-Python package listed in `pure_python_packages` with `in_pyodide_cdn=true` has a version in the lock file that differs from the locally installed version
- **THEN** a warning SHALL be reported indicating the version mismatch
- **AND** the build SHALL continue (the local version will be used for SSR while the CDN version is recorded in the lock file)
- **AND** the warning SHALL note that the local version will be used for SSR/SSG

#### Scenario: WASM package not locally installed
- **WHEN** a package listed in `wasm_packages` is not found in the local environment
- **THEN** a warning SHALL be reported indicating the package is needed locally for SSR/SSG
- **AND** the build SHALL continue

#### Scenario: WASM package version mismatch
- **WHEN** a WASM package listed in `wasm_packages` has a version in the lock file that differs from the locally installed version
- **THEN** a warning SHALL be reported indicating the version mismatch
- **AND** the build SHALL continue (the local version will be used for SSR/SSG)
- **AND** the warning SHALL note that the local version will be used for SSR/SSG
