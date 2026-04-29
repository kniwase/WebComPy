# Dependency Resolver — Delta: feat-deps-local-serving

## MODIFIED Requirements

### Requirement: Dependencies shall be classified using Pyodide lock data with delivery-mode awareness
Dependency classification SHALL consult the Pyodide lock file to determine if a package is available from the Pyodide CDN. The delivery mechanism is determined at build time by `AppConfig.serve_all_deps`, not at classification time. `ClassifiedDependency` SHALL separate the concerns of package availability (`in_pyodide_cdn`) from package type (`is_wasm`).

#### Scenario: Pure-Python package in Pyodide CDN with serve_all_deps=True
- **WHEN** a dependency `httpx` is found in the Pyodide lock and is not a WASM package
- **THEN** `httpx` SHALL be classified with `is_wasm=False`, `is_pure_python=True`, `in_pyodide_cdn=True`
- **AND** `httpx` SHALL have `pyodide_file_name` and `pyodide_sha256` populated
- **WHEN** `serve_all_deps=True`
- **THEN** `httpx` SHALL be downloaded from the Pyodide CDN and bundled into the app wheel

#### Scenario: Pure-Python package in Pyodide CDN with serve_all_deps=False
- **WHEN** a dependency `httpx` is found in the Pyodide lock and is not a WASM package
- **AND** `serve_all_deps=False`
- **THEN** `httpx` SHALL NOT be bundled into the app wheel
- **AND** `httpx` SHALL appear in `py-config.packages` as a plain package name

#### Scenario: Pure-Python package not in Pyodide CDN
- **WHEN** a dependency `flask` is not found in the Pyodide lock
- **AND** `flask`'s installed package directory contains no `.so`, `.pyd`, or `.dylib` files
- **THEN** `flask` SHALL be classified with `is_pure_python=True`, `in_pyodide_cdn=False`
- **AND** `flask` SHALL be bundled into the app wheel (regardless of `serve_all_deps`)

#### Scenario: WASM package (regardless of serve_all_deps)
- **WHEN** a dependency `numpy` is found in the Pyodide lock and is a WASM package
- **THEN** `numpy` SHALL be classified with `is_wasm=True`, `in_pyodide_cdn=True`
- **AND** `numpy` SHALL always appear in `py-config.packages` as a plain package name

### Requirement: ClassifiedDependency shall separate availability from delivery
`ClassifiedDependency` SHALL have the following fields:
- `name: str`
- `version: str`
- `source: Literal["explicit", "transitive"]` — whether the developer listed it or it was auto-discovered
- `is_wasm: bool` — whether the package is a WASM package (must come from CDN)
- `is_pure_python: bool` — whether the package is pure-Python
- `in_pyodide_cdn: bool` — whether the package exists in the Pyodide CDN
- `pyodide_file_name: str | None` — the `.whl` file name from the Pyodide lock (when `in_pyodide_cdn=True`)
- `pyodide_sha256: str | None` — the SHA256 hash from the Pyodide lock (when `in_pyodide_cdn=True`)
- `pkg_dir: pathlib.Path | None` — the local package directory path (when installed locally)

The previous `source` values `"pyodide_cdn"` and `"fallback_cdn"` are removed. The previous `is_bundled` and `is_cdn_package` properties are removed.

## ADDED Requirements

### Requirement: Transitive dependencies shall be resolved via Pyodide lock with local metadata fallback
Transitive dependencies SHALL be resolved using the Pyodide lock `depends` field as the primary source and local `importlib.metadata` as a best-effort fallback for packages not in the lock. This enables more complete dependency discovery when `serve_all_deps=True`.

#### Scenario: Transitive dependency in Pyodide lock
- **WHEN** `httpx` depends on `httpcore` and `h2`, both in the Pyodide lock
- **THEN** `httpcore` and `h2` SHALL be discovered by recursively walking the `depends` field
- **AND** they SHALL be classified with `in_pyodide_cdn=True` and appropriate CDN metadata

#### Scenario: Transitive dependency not in Pyodide lock but installed locally
- **WHEN** `flask` depends on `click` and `click` is not in the Pyodide lock
- **AND** `click` is installed locally
- **THEN** `click` SHALL be discovered via `importlib.metadata.requires()` fallback
- **AND** `click` SHALL be classified with `in_pyodide_cdn=False`

#### Scenario: Transitive dependency not in lock and not installed locally
- **WHEN** a transitive dependency is not found in the Pyodide lock and not installed locally
- **THEN** a warning SHALL be reported (not an error)
- **AND** the developer SHALL be instructed to add the dependency to `AppConfig.dependencies`

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