# Dependency Resolver — Delta: feat-dependency-bundling

## ADDED Requirements

### Requirement: Dependencies shall be classified using Pyodide lock data as primary source
Dependency classification SHALL first consult the Pyodide lock file (`pyodide-lock.json`) to determine if a package is available from the Pyodide CDN. **WASM packages** in the Pyodide lock SHALL be loaded from the CDN by name via `py-config.packages`. **Pure-Python packages** in the Pyodide lock SHALL be bundled into the app wheel and served locally. Packages not in the Pyodide lock SHALL be resolved locally and classified as bundled (pure-Python) or error (C extension).

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
- **AND** `httpx` SHALL be bundled into the app wheel and served locally
- **AND** `httpx` SHALL NOT appear in `py-config.packages`

#### Scenario: Pure-Python package not in Pyodide CDN
- **WHEN** a dependency `flask` is not found in the Pyodide lock
- **AND** `flask`'s installed package directory contains no `.so` or `.pyd` files
- **THEN** `flask` SHALL be classified as `bundled` with `source="explicit"`
- **AND** `flask` SHALL be bundled into the app wheel

#### Scenario: C extension package not in Pyodide CDN
- **WHEN** a dependency `some_c_ext` is not found in the Pyodide lock
- **AND** `some_c_ext`'s installed package directory contains `.so` or `.pyd` files
- **THEN** an error SHALL be reported indicating the package is a C extension not available in Pyodide
- **AND** the build SHALL fail with a descriptive message

### Requirement: Transitive dependencies shall be resolved recursively
Transitive dependencies SHALL be resolved for all packages. For packages not in the Pyodide CDN, `importlib.metadata` is used to walk locally-installed package metadata. For pure-Python packages in the Pyodide CDN, the Pyodide lock `depends` field is used as a hint to discover transitive dependencies within the CDN, falling back to local `importlib.metadata` for dependencies not in the lock.

**Limitation**: Transitive dependency resolution depends on the build environment. If a dependency (or its transitive dependency) is not installed locally and not discoverable from the Pyodide lock, the build SHALL report an error. Complete transitive resolution without local installation is a goal of the standalone build mode (`feat-standalone-build`), which will download wheels from the Pyodide CDN.

#### Scenario: Transitive pure-Python dependency resolution (local package)
- **WHEN** `flask` is in `AppConfig.dependencies` and not in the Pyodide CDN
- **AND** `flask` depends on `click`, `itsdangerous`, and `jinja2`
- **AND** `click` and `itsdangerous` are not in the Pyodide CDN and are pure-Python
- **AND** `jinja2` is in the Pyodide CDN and is a pure-Python package
- **AND** all packages are installed locally
- **THEN** `click` and `itsdangerous` SHALL be classified as `bundled` with `source="transitive"`
- **AND** `jinja2` SHALL be classified as `pyodide_cdn` with `is_wasm=False`
- **AND** `jinja2` SHALL be bundled into the app wheel
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
- **AND** `sniffio` SHALL be classified as `bundled` with `source="transitive"` (resolved via local `importlib.metadata`)
- **AND** all pure-Python packages SHALL be bundled into the app wheel
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

### Requirement: The Pyodide lock shall be fetched from CDN with local caching
The Pyodide lock file SHALL be fetched from `https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json` and cached locally at `~/.cache/webcompy/pyodide-lock-{version}.json`. The Pyodide version SHALL be derived from the PyScript version via a mapping table.

#### Scenario: Fetching Pyodide lock for the first time
- **WHEN** the Pyodide lock cache does not exist for the required version
- **THEN** it SHALL be fetched from the CDN and saved to the cache directory

#### Scenario: Using cached Pyodide lock
- **WHEN** the Pyodide lock cache exists for the required version
- **THEN** the cached file SHALL be used without network requests

#### Scenario: Network failure with no cache
- **WHEN** the CDN is unreachable and no cache exists
- **THEN** all dependencies SHALL fall back to `py-config.packages` as plain package names
- **AND** `.so`/`.pyd` detection SHALL still be performed locally for locally-installed packages
- **AND** C-extension packages not found locally SHALL produce a warning (not an error, since Pyodide may provide them)
- **AND** pure-Python packages not found locally SHALL also be listed in `py-config.packages`, trusting Pyodide/micropip to resolve them

### Requirement: The PyScript version shall map to a Pyodide version
The PyScript version used in generated HTML (`PYSCRIPT_VERSION`) SHALL map to a specific Pyodide version for lock file resolution.

#### Scenario: Mapping PyScript 2026.3.1
- **WHEN** the PyScript version is `2026.3.1`
- **THEN** the Pyodide version SHALL be `0.29.3`