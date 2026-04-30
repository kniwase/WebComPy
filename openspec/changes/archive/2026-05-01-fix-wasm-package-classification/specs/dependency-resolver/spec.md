## MODIFIED Requirements

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