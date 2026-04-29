# Dependency Resolver

## Purpose

The dependency resolver classifies application dependencies for browser deployment. It determines which packages can be loaded from the Pyodide CDN (WASM packages by name) and which must be bundled locally (pure-Python packages not in the CDN). This classification drives lock file generation and wheel bundling decisions.

## Requirements

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

The previous `source` values `"pyodide_cdn"` and `"fallback_cdn"` SHALL NOT be used. The previous `is_bundled` and `is_cdn_package` properties SHALL NOT be present.

#### Scenario: Explicit dependency with CDN availability
- **WHEN** a developer lists `httpx` in `AppConfig.dependencies`
- **AND** `httpx` is available in the Pyodide CDN as a pure-Python package
- **THEN** `ClassifiedDependency` SHALL have `source="explicit"`, `in_pyodide_cdn=True`, `pyodide_file_name` and `pyodide_sha256` populated
- **AND** `is_bundled` and `is_cdn_package` SHALL NOT be present

#### Scenario: Transitive local-only dependency
- **WHEN** `flask` is auto-discovered as a transitive dependency
- **AND** `flask` is not available in the Pyodide CDN
- **THEN** `ClassifiedDependency` SHALL have `source="transitive"`, `in_pyodide_cdn=False`, `pyodide_file_name=None`, `pyodide_sha256=None`

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

#### Scenario: Non-WASM Pyodide CDN package version mismatch
- **WHEN** a non-WASM Pyodide CDN package (`in_pyodide_cdn=True`, `is_wasm=False`) has a local version that differs from the lock file
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