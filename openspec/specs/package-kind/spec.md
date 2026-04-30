# Package Kind

## Purpose

The `PackageKind` enumeration defines the mutually exclusive categories for classifying application dependencies for browser deployment. It provides a single source of truth for whether a package requires WASM runtime, is available as pure-Python from the Pyodide CDN, or must be bundled from local installation. This classification drives lock file generation, wheel bundling, and `py-config.packages` construction.

## Requirements

### Requirement: PackageKind shall classify packages into three mutually exclusive categories
`PackageKind` SHALL be an enumeration with three members: `WASM` (packages containing WebAssembly-compiled native extensions that must be loaded from the Pyodide CDN by name), `CDN_PURE_PYTHON` (pure-Python packages available in the Pyodide CDN that can be bundled or loaded by name), and `LOCAL_PURE_PYTHON` (pure-Python packages not available in the Pyodide CDN that must be bundled from local installation). A package SHALL belong to exactly one category.

#### Scenario: PackageKind enum values
- **WHEN** code references `PackageKind`
- **THEN** `PackageKind.WASM`, `PackageKind.CDN_PURE_PYTHON`, and `PackageKind.LOCAL_PURE_PYTHON` SHALL be the only valid values
- **AND** each value SHALL be mutually exclusive with the others

### Requirement: WASM packages shall be identified by wheel filename platform tag
The classification function SHALL determine whether a Pyodide CDN package is WASM by inspecting the `file_name` field from the Pyodide lock. A wheel filename containing `"wasm32"` in its platform tag indicates a WASM-compiled package. The `package_type` field from the Pyodide lock SHALL NOT be used for WASM detection, as it is unreliable across Pyodide versions.

#### Scenario: WASM package detection via filename
- **WHEN** a package in the Pyodide lock has `file_name` containing `"wasm32"` (e.g., `numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl`)
- **THEN** the package SHALL be classified as `PackageKind.WASM`

#### Scenario: Pure-Python CDN package detection via filename
- **WHEN** a package in the Pyodide lock has `file_name` not containing `"wasm32"` (e.g., `packaging-24.2-py3-none-any.whl`)
- **THEN** the package SHALL be classified as `PackageKind.CDN_PURE_PYTHON`

#### Scenario: Package not in Pyodide lock
- **WHEN** a dependency is not found in the Pyodide lock
- **AND** the locally installed package directory contains no `.so`, `.pyd`, or `.dylib` files
- **THEN** the package SHALL be classified as `PackageKind.LOCAL_PURE_PYTHON`

#### Scenario: Local C-extension package not in Pyodide lock
- **WHEN** a dependency is not found in the Pyodide lock
- **AND** the locally installed package directory contains `.so`, `.pyd`, or `.dylib` files
- **THEN** an error SHALL be reported indicating the package cannot be used in the browser

### Requirement: ClassifiedDependency shall use PackageKind instead of overlapping booleans
`ClassifiedDependency` SHALL use a `kind: PackageKind` field instead of separate `is_wasm`, `is_pure_python`, and `in_pyodide_cdn` boolean fields. The `kind` field SHALL be the single source of truth for package categorization. The boolean fields `is_wasm`, `is_pure_python`, and `in_pyodide_cdn` SHALL NOT exist on `ClassifiedDependency`.

#### Scenario: WASM package classification
- **WHEN** numpy is classified from the Pyodide lock with a `wasm32` wheel filename
- **THEN** `ClassifiedDependency.kind` SHALL be `PackageKind.WASM`
- **AND** `is_wasm`, `is_pure_python`, and `in_pyodide_cdn` SHALL NOT be present as fields

#### Scenario: CDN pure-Python package classification
- **WHEN** packaging is classified from the Pyodide lock with a `py3-none-any` wheel filename
- **THEN** `ClassifiedDependency.kind` SHALL be `PackageKind.CDN_PURE_PYTHON`

#### Scenario: Local pure-Python package classification
- **WHEN** flask is not found in the Pyodide lock and is a locally installed pure-Python package
- **THEN** `ClassifiedDependency.kind` SHALL be `PackageKind.LOCAL_PURE_PYTHON`

### Requirement: ClassifiedDependency shall retain source, version, and Pyodide metadata fields
`ClassifiedDependency` SHALL retain `name: str`, `version: str`, `source: Literal["explicit", "transitive"]`, `pyodide_file_name: str | None`, `pyodide_sha256: str | None`, and `pkg_dir: pathlib.Path | None` fields. The `pyodide_file_name` and `pyodide_sha256` fields SHALL be populated when `kind` is `WASM` or `CDN_PURE_PYTHON`. The `pkg_dir` field SHALL be populated when `kind` is `LOCAL_PURE_PYTHON` or when the package is installed locally for `CDN_PURE_PYTHON`.

#### Scenario: WASM package metadata
- **WHEN** numpy is classified as `PackageKind.WASM`
- **THEN** `pyodide_file_name` SHALL be the wheel filename from the Pyodide lock
- **AND** `pyodide_sha256` SHALL be the SHA256 hash from the Pyodide lock

#### Scenario: Local pure-Python package metadata
- **WHEN** flask is classified as `PackageKind.LOCAL_PURE_PYTHON`
- **THEN** `pkg_dir` SHALL be the local package directory path
- **AND** `pyodide_file_name` and `pyodide_sha256` SHALL be `None`