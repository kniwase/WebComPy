# Dependency Resolver

## Purpose

The dependency resolver classifies application dependencies for browser deployment. It determines which packages can be loaded from the Pyodide CDN (WASM packages by name) and which must be bundled locally (pure-Python packages not in the CDN). This classification drives lock file generation and wheel bundling decisions.

## Requirements

### Requirement: Dependencies shall be classified using Pyodide lock data with delivery-mode-aware PackageKind
Dependency classification SHALL consult the Pyodide lock file to determine if a package is available from the Pyodide CDN and what kind of package it is. The `ClassifiedDependency` dataclass SHALL use a `kind: PackageKind` enum field instead of separate `is_wasm`, `is_pure_python`, and `in_pyodide_cdn` boolean fields. `PackageKind` has three values: `WASM` (WASM-compiled, must load from CDN), `CDN_PURE_PYTHON` (pure-Python, available on CDN), and `LOCAL_PURE_PYTHON` (pure-Python, not on CDN, must bundle locally). The `in_pyodide_cdn` information is derived from `kind != LOCAL_PURE_PYTHON`.

#### Scenario: WASM package classification
- **WHEN** a dependency `numpy` is found in the Pyodide lock and its wheel filename contains `wasm32`
- **THEN** `numpy` SHALL be classified with `kind=PackageKind.WASM`
- **AND** `kind != PackageKind.LOCAL_PURE_PYTHON` SHALL be `True` (i.e., `in_pyodide_cdn` is `True`)

#### Scenario: CDN pure-Python package classification
- **WHEN** a dependency `httpx` is found in the Pyodide lock and its wheel filename does not contain `wasm32`
- **THEN** `httpx` SHALL be classified with `kind=PackageKind.CDN_PURE_PYTHON`
- **AND** `kind != PackageKind.LOCAL_PURE_PYTHON` SHALL be `True` (i.e., `in_pyodide_cdn` is `True`)

#### Scenario: Local pure-Python package classification
- **WHEN** a dependency `flask` is NOT found in the Pyodide lock
- **AND** `flask`'s installed package directory contains no `.so`, `.pyd`, or `.dylib` files
- **THEN** `flask` SHALL be classified with `kind=PackageKind.LOCAL_PURE_PYTHON`
- **AND** `kind != PackageKind.LOCAL_PURE_PYTHON` SHALL be `False` (i.e., `in_pyodide_cdn` is `False`)

#### Scenario: C extension package not in Pyodide CDN
- **WHEN** a dependency is NOT found in the Pyodide lock
- **AND** its installed package directory contains `.so`, `.pyd`, or `.dylib` files
- **THEN** an error SHALL be reported indicating the package cannot be used in the browser
- **AND** the build SHALL fail

### Requirement: WASM detection shall use wheel filename platform tag
WASM package detection in `classify_dependencies()` SHALL use the classification function defined in the `package-kind` capability (see `specs/package-kind/spec.md`). The `package_type` field in the Pyodide lock SHALL NOT be used for WASM detection.

#### Scenario: Classification delegates to PackageKind-based detection
- **WHEN** `classify_dependencies()` encounters a package in the Pyodide lock
- **THEN** it SHALL use the `PackageKind`-based classification function to determine the package kind
- **AND** it SHALL NOT reference the `package_type` field from the Pyodide lock

### Requirement: ClassifiedDependency shall use PackageKind enum
`ClassifiedDependency` SHALL have the following fields:
- `name: str`
- `version: str`
- `source: Literal["explicit", "transitive"]` — whether the developer listed it or it was auto-discovered
- `kind: PackageKind` — the package category (`WASM`, `CDN_PURE_PYTHON`, or `LOCAL_PURE_PYTHON`)
- `pyodide_file_name: str | None` — the `.whl` file name from the Pyodide lock (when `kind != LOCAL_PURE_PYTHON`)
- `pyodide_sha256: str | None` — the SHA256 hash from the Pyodide lock (when `kind != LOCAL_PURE_PYTHON`)
- `pkg_dir: pathlib.Path | None` — the local package directory path (when `kind == LOCAL_PURE_PYTHON`)

The previous `is_wasm`, `is_pure_python`, and `in_pyodide_cdn` boolean fields SHALL NOT be present. The previous `source` values `"pyodide_cdn"` and `"fallback_cdn"` SHALL NOT be used.

#### Scenario: Explicit WASM dependency
- **WHEN** a developer lists `numpy` in `AppConfig.dependencies`
- **AND** `numpy` is available in the Pyodide CDN as a WASM package
- **THEN** `ClassifiedDependency` SHALL have `source="explicit"`, `kind=PackageKind.WASM`, `pyodide_file_name` and `pyodide_sha256` populated
- **AND** `is_wasm`, `is_pure_python`, and `in_pyodide_cdn` SHALL NOT be present

#### Scenario: Explicit CDN pure-Python dependency
- **WHEN** a developer lists `httpx` in `AppConfig.dependencies`
- **AND** `httpx` is available in the Pyodide CDN as a pure-Python package
- **THEN** `ClassifiedDependency` SHALL have `source="explicit"`, `kind=PackageKind.CDN_PURE_PYTHON`, `pyodide_file_name` and `pyodide_sha256` populated

#### Scenario: Transitive local-only dependency
- **WHEN** `flask` is auto-discovered as a transitive dependency
- **AND** `flask` is not available in the Pyodide CDN
- **THEN** `ClassifiedDependency` SHALL have `source="transitive"`, `kind=PackageKind.LOCAL_PURE_PYTHON`, `pyodide_file_name=None`, `pyodide_sha256=None`

### Requirement: Transitive dependencies shall be resolved via Pyodide lock with local metadata fallback
Transitive dependencies SHALL be resolved using the Pyodide lock `depends` field as the primary source and local `importlib.metadata` as a best-effort fallback for packages not in the lock. This enables more complete dependency discovery when `serve_all_deps=True`.

#### Scenario: Transitive dependency in Pyodide lock
- **WHEN** `httpx` depends on `httpcore` and `h2`, both in the Pyodide lock
- **THEN** `httpcore` and `h2` SHALL be discovered by recursively walking the `depends` field
- **AND** they SHALL be classified with `kind=PackageKind.CDN_PURE_PYTHON` or `kind=PackageKind.WASM` and appropriate CDN metadata

#### Scenario: Transitive dependency not in Pyodide lock but installed locally
- **WHEN** `flask` depends on `click` and `click` is not in the Pyodide lock
- **AND** `click` is installed locally
- **THEN** `click` SHALL be discovered via `importlib.metadata.requires()` fallback
- **AND** `click` SHALL be classified with `in_pyodide_cdn=False`

#### Scenario: Transitive dependency not in lock and not installed locally
- **WHEN** a transitive dependency is not found in the Pyodide lock and not installed locally
- **THEN** a warning SHALL be reported (not an error)
- **AND** the developer SHALL be instructed to add the dependency to `AppConfig.dependencies`

### Requirement: Locally bundled packages shall be verified at build time
When resolving a lock file for bundling (via `get_bundled_deps()` or equivalent), the resolver SHALL verify that each package expected to be bundled is actually present in the local Python environment. This ensures SSR/SSG consistency: the version used by the CPython server for pre-rendering MUST match the version bundled into the browser wheel.

#### Scenario: Package found locally and version matches lock file
- **WHEN** a bundled package with lock file version `2.1.5` is found in the local environment via `importlib.util.find_spec()`
- **AND** `importlib.metadata.version()` reports version `2.1.5`
- **THEN** the package directory SHALL be included in the bundled deps list

#### Scenario: Local-only package not found locally
- **WHEN** a local-only package (`in_pyodide_cdn=False`) expected to be bundled is not found in the local environment via `importlib.util.find_spec()`
- **THEN** the resolver SHALL report an error with the package name and lock file version
- **AND** the error message SHALL include an installation command (e.g., `pip install <package>==<version>`)
- **AND** the build SHALL fail

#### Scenario: Package found locally but version differs from lock file
- **WHEN** a bundled package with lock file version `2.1.5` is found in the local environment
- **AND** `importlib.metadata.version()` reports a different version (e.g., `3.0.2`)
- **THEN** the resolver SHALL report an error indicating the version mismatch
- **AND** the error message SHALL include the expected (lock file) version and the actual (local) version
- **AND** the error message SHALL suggest installing the lock file version (e.g., `pip install <package>==2.1.5`)
- **AND** the build SHALL fail

#### Scenario: CDN pure-Python package version mismatch
- **WHEN** a CDN pure-Python package (in `pure_python_packages` with `in_pyodide_cdn=True`) has a local version that differs from the lock file
- **THEN** a warning SHALL be reported (not an error) indicating the version mismatch
- **AND** the local version SHALL be used for SSR/SSG
- **AND** the build SHALL continue

### Requirement: Local environment validation SHALL consider serve_all_deps and CDN availability
`validate_local_environment()` SHALL differentiate between CDN-available and local-only packages, and adjust error severity based on `serve_all_deps`.

#### Scenario: CDN-available package missing locally with serve_all_deps=True
- **WHEN** a pure-Python package with `in_pyodide_cdn=True` is not installed locally
- **AND** `serve_all_deps=True`
- **THEN** a warning SHALL be reported (not an error)
- **AND** the build SHALL continue (the package will be downloaded from CDN)

#### Scenario: CDN-available package missing locally with serve_all_deps=False
- **WHEN** a pure-Python package with `in_pyodide_cdn=True` is not installed locally
- **AND** `serve_all_deps=False`
- **THEN** a warning SHALL be reported (not an error)
- **AND** the build SHALL continue (the package will be loaded from CDN in the browser)

#### Scenario: Local-only package missing locally
- **WHEN** a pure-Python package with `in_pyodide_cdn=False` is not installed locally
- **THEN** an error SHALL be reported regardless of `serve_all_deps`
- **AND** the build SHALL fail

### Requirement: The Pyodide lock shall be fetched from CDN with local caching
The Pyodide lock file SHALL be fetched from `https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json` and cached locally at `~/.cache/webcompy/pyodide-lock-{version}.json`. The Pyodide version SHALL be derived from the PyScript version via a mapping table. If the fetch fails and no cache exists, a `PyodideLockFetchError` SHALL be raised.

#### Scenario: Fetching Pyodide lock for the first time
- **WHEN** the Pyodide lock cache does not exist for the required version
- **THEN** it SHALL be fetched from the CDN and saved to the cache directory

#### Scenario: Using cached Pyodide lock
- **WHEN** the Pyodide lock cache exists for the required version
- **THEN** the cached file SHALL be used without network requests

#### Scenario: Network failure with no cache
- **WHEN** the CDN is unreachable and no cache exists
- **THEN** a `PyodideLockFetchError` SHALL be raised
- **AND** the error message SHALL indicate that network access is required

#### Scenario: Invalid response from CDN
- **WHEN** the CDN returns a response that cannot be parsed as valid JSON
- **THEN** a `PyodideLockFetchError` SHALL be raised
- **AND** the error message SHALL indicate that the CDN data was invalid

### Requirement: The PyScript version shall map to a Pyodide version
The PyScript version used in generated HTML (`PYSCRIPT_VERSION`) SHALL map to a specific Pyodide version for lock file resolution.

#### Scenario: Mapping PyScript 2026.3.1
- **WHEN** the PyScript version is `2026.3.1`
- **THEN** the Pyodide version SHALL be `0.29.3`