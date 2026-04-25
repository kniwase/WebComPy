# Dependency Resolver — Delta: feat-dependency-bundling

## ADDED Requirements

### Requirement: Dependencies shall be classified using Pyodide lock data as primary source
Dependency classification SHALL consult the Pyodide lock file (`pyodide-lock.json`) to determine if a package is available from the Pyodide CDN. **WASM packages** in the Pyodide lock SHALL be loaded from the CDN by name via `py-config.packages`. **Pure-Python packages** in the Pyodide lock SHALL be served from the Pyodide CDN (they are already available and do not need bundling). Packages not in the Pyodide lock SHALL be resolved locally and classified as bundled (pure-Python) or error (C extension). The Pyodide lock is **required** for dependency resolution; if it cannot be fetched and no cached version exists, the build SHALL fail with a descriptive error.

#### Scenario: WASM package available in Pyodide CDN
- **WHEN** a dependency `numpy` is listed in `AppConfig.dependencies`
- **AND** `numpy` is found in the Pyodide lock and is a WASM package
- **THEN** `numpy` SHALL be classified as `pyodide_cdn` with `is_wasm=True`
- **AND** `numpy` SHALL appear in `py-config.packages` as a plain package name
- **AND** `numpy` SHALL NOT be bundled into the app wheel

#### Scenario: Pure-Python package available in Pyodide CDN
- **WHEN** a dependency `httpx` is listed in `AppConfig.dependencies`
- **AND** `httpx` is found in the Pyodide lock and is a pure-Python package
- **THEN** `httpx` SHALL be classified as `pyodide_cdn` with `is_wasm=False`
- **AND** `httpx` SHALL NOT be bundled into the app wheel
- **AND** `httpx` SHALL NOT appear in `py-config.packages`

#### Scenario: Pure-Python package not in Pyodide CDN
- **WHEN** a dependency `flask` is not found in the Pyodide lock
- **AND** `flask`'s installed package directory contains no `.so`, `.pyd`, or `.dylib` files
- **THEN** `flask` SHALL be classified as `bundled` with `source="explicit"`
- **AND** `flask` SHALL be bundled into the app wheel

#### Scenario: C extension package not in Pyodide CDN
- **WHEN** a dependency `some_c_ext` is not found in the Pyodide lock
- **AND** `some_c_ext`'s installed package directory contains `.so`, `.pyd`, or `.dylib` files
- **THEN** an error SHALL be reported indicating the package is a C extension not available in Pyodide
- **AND** the build SHALL fail with a descriptive message

#### Scenario: Pyodide lock fetch failure
- **WHEN** the Pyodide lock cannot be fetched (network failure, no cache)
- **AND** no cached version exists
- **THEN** the build SHALL fail with a descriptive error
- **AND** the error message SHALL indicate that network access is required or suggest running `webcompy lock` in an environment with internet access

### Requirement: Transitive dependencies shall be resolved via Pyodide lock depends chain
Transitive dependencies SHALL be resolved using the Pyodide lock `depends` field. This scoping ensures that only dependencies relevant to the browser runtime are included, and prevents dev/build-only packages from leaking into the lock file. For packages not in the Pyodide lock but found locally, the local `importlib.metadata` is used only for version detection and purity classification — NOT for walking the dependency graph.

**Limitation**: Transitive dependency resolution for locally-bundled packages (those not in the Pyodide CDN) depends on the Pyodide lock's awareness of them. If a locally-bundled package has transitive dependencies that are not in the Pyodide lock and not installed locally, the build SHALL report an error. Complete transitive resolution without Pyodide lock coverage is a goal of the standalone build mode (`feat-standalone-build`).

#### Scenario: Transitive pure-Python dependency resolution (local package)
- **WHEN** `flask` is in `AppConfig.dependencies` and not in the Pyodide CDN
- **AND** `flask` depends on `click`, `itsdangerous`, and `jinja2`
- **AND** `click` and `itsdangerous` are not in the Pyodide CDN and are pure-Python
- **AND** `jinja2` is in the Pyodide CDN and is a pure-Python package
- **AND** all packages are installed locally
- **THEN** `click` and `itsdangerous` SHALL be classified as `bundled` with `source="transitive"`
- **AND** `jinja2` SHALL be classified as `pyodide_cdn` with `is_wasm=False`
- **AND** `jinja2` SHALL NOT be bundled into the app wheel
- **AND** `jinja2` SHALL NOT appear in `py-config.packages`

#### Scenario: Transitive dependency resolution for Pyodide CDN pure-Python packages
- **WHEN** `httpx` is in `AppConfig.dependencies` and is a pure-Python package in the Pyodide CDN
- **AND** `httpx` depends on `httpcore`, `sniffio`, and `h2`
- **AND** `httpcore` and `h2` are also pure-Python packages in the Pyodide CDN
- **AND** `sniffio` is not in the Pyodide CDN but is installed locally as pure-Python
- **AND** the Pyodide lock `depends` field for `httpx` lists `httpcore` and `h2`
- **THEN** `httpx` SHALL be classified as `pyodide_cdn` with `is_wasm=False` and source `"explicit"`
- **AND** `httpcore` and `h2` SHALL be resolved via the Pyodide lock `depends` field
- **AND** `httpcore` and `h2` SHALL be classified as `pyodide_cdn` with `is_wasm=False` and source `"transitive"`
- **AND** `sniffio` SHALL be classified as `bundled` with `source="transitive"`
- **AND** only WASM packages SHALL appear in `py-config.packages`

#### Scenario: Transitive dependency not installed locally and not in Pyodide lock
- **WHEN** a transitive dependency is not found in the Pyodide lock and not installed locally
- **THEN** the build SHALL report an error indicating the missing dependency
- **AND** the developer SHALL be instructed to install it locally or add it to `AppConfig.dependencies`

#### Scenario: Transitive WASM dependency of a Pyodide CDN pure-Python package
- **WHEN** `httpx` is in `AppConfig.dependencies` and is a pure-Python package in the Pyodide CDN
- **AND** `httpx` depends on `httpcore` which is a WASM package in the Pyodide CDN
- **THEN** `httpcore` SHALL be classified as `pyodide_cdn` with `is_wasm=True`
- **AND** `httpcore` SHALL appear in `py-config.packages` as a plain package name
- **AND** `httpcore` SHALL NOT be bundled into the app wheel

#### Scenario: Transitive C extension dependency
- **WHEN** a transitive dependency is a C extension not in the Pyodide CDN
- **THEN** an error SHALL be reported

### Requirement: Locally bundled packages shall be verified at build time
When resolving a lock file for bundling (via `get_bundled_deps()` or equivalent), the resolver SHALL verify that each package expected to be bundled is actually present in the local Python environment. This ensures SSR/SSG consistency: the version used by the CPython server for pre-rendering MUST match the version bundled into the browser wheel.

#### Scenario: Package found locally and version matches lock file
- **WHEN** a bundled package with lock file version `2.1.5` is found in the local environment via `importlib.util.find_spec()`
- **AND** `importlib.metadata.version()` reports version `2.1.5`
- **THEN** the package directory SHALL be included in the bundled deps list

#### Scenario: Package not found locally
- **WHEN** a bundled package is not found in the local environment via `importlib.util.find_spec()`
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
- **WHEN** a non-WASM Pyodide CDN package (served from the Pyodide CDN) has a local version that differs from the lock file
- **THEN** a warning SHALL be reported (not an error) indicating the version mismatch
- **AND** the local version SHALL be used for SSR/SSG
- **AND** the build SHALL continue

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