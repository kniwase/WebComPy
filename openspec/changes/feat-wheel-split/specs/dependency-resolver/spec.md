# Dependency Resolver — Delta: feat-wheel-split

## ADDED Requirements

### Requirement: Dependencies shall be classified using Pyodide lock data as primary source
Dependency classification SHALL first consult the Pyodide lock file (`pyodide-lock.json`) to determine if a package is available from the Pyodide CDN. Packages in the Pyodide lock SHALL be listed in `py-config.packages` by name. Packages not in the Pyodide lock SHALL be resolved locally and classified as bundled (pure-Python) or error (C extension).

#### Scenario: Package available in Pyodide CDN
- **WHEN** a dependency `numpy` is listed in `AppConfig.dependencies`
- **AND** `numpy` is found in the Pyodide lock
- **THEN** `numpy` SHALL be classified as `pyodide_cdn`
- **AND** `numpy` SHALL appear in `py-config.packages` as a plain package name
- **AND** `numpy` SHALL NOT be bundled into the app wheel

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
Dependencies not in the Pyodide CDN SHALL have their transitive dependencies resolved via `importlib.metadata`. Each transitive dependency SHALL be classified using the same logic (Pyodide lock → local `.so` check).

#### Scenario: Transitive pure-Python dependency resolution
- **WHEN** `flask` is in `AppConfig.dependencies` and not in the Pyodide CDN
- **AND** `flask` depends on `click`, `itsdangerous`, and `jinja2`
- **AND** `click` and `itsdangerous` are not in the Pyodide CDN and are pure-Python
- **AND** `jinja2` is in the Pyodide CDN
- **THEN** `click` and `itsdangerous` SHALL be classified as `bundled` with `source="transitive"`
- **AND** `jinja2` SHALL be classified as `pyodide_cdn`

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
- **THEN** dependencies SHALL be classified using local heuristics only (fallback to `py-config.packages` for all dependencies)

### Requirement: The PyScript version shall map to a Pyodide version
The PyScript version used in generated HTML (`PYSCRIPT_VERSION`) SHALL map to a specific Pyodide version for lock file resolution.

#### Scenario: Mapping PyScript 2026.3.1
- **WHEN** the PyScript version is `2026.3.1`
- **THEN** the Pyodide version SHALL be `0.29.3`