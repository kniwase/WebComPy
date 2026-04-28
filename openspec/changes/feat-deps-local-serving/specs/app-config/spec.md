# App Configuration — Delta: feat-deps-local-serving

## ADDED Requirements

### Requirement: AppConfig shall include a serve_all_deps field for controlling dependency delivery
`AppConfig` SHALL include a `serve_all_deps: bool = True` field. When `True` (default), all pure-Python packages that the WebComPy server can provide are served from the same origin — either bundled from local installation or downloaded from the Pyodide CDN and then bundled. When `False`, pure-Python packages available in the Pyodide CDN are loaded from the CDN by name via `py-config.packages`, and only packages not available from the CDN are bundled.

#### Scenario: Default serve_all_deps behavior
- **WHEN** a developer creates `AppConfig()` without `serve_all_deps`
- **THEN** `serve_all_deps` SHALL be `True`
- **AND** all pure-Python packages SHALL be bundled into the app wheel
- **AND** only WASM package names SHALL appear in `py-config.packages`

#### Scenario: Explicit serve_all_deps=True
- **WHEN** a developer creates `AppConfig(serve_all_deps=True)`
- **THEN** pure-Python packages in the Pyodide CDN SHALL be downloaded at build time and bundled into the app wheel
- **AND** pure-Python packages NOT in the Pyodide CDN SHALL be bundled from local installation
- **AND** only WASM package names SHALL appear in `py-config.packages`

#### Scenario: Explicit serve_all_deps=False
- **WHEN** a developer creates `AppConfig(serve_all_deps=False)`
- **THEN** pure-Python packages in the Pyodide CDN SHALL NOT be bundled
- **AND** their package names SHALL appear in `py-config.packages` for CDN loading
- **AND** pure-Python packages NOT in the Pyodide CDN SHALL be bundled from local installation
- **AND** WASM package names SHALL appear in `py-config.packages`

### Requirement: CLI flags shall override serve_all_deps
The `start` and `generate` CLI subcommands SHALL accept `--serve-all-deps` and `--no-serve-all-deps` flags that override `AppConfig.serve_all_deps`.

#### Scenario: Overriding with --no-serve-all-deps
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **THEN** `serve_all_deps` SHALL be `False` for the session
- **AND** CDN-available pure-Python packages SHALL be loaded from CDN

#### Scenario: Overriding with --serve-all-deps
- **WHEN** a developer runs `python -m webcompy generate --serve-all-deps`
- **THEN** `serve_all_deps` SHALL be `True` for the session
- **AND** CDN-available pure-Python packages SHALL be downloaded and bundled

## MODIFIED Requirements

### Requirement: Pure-Python packages in the Pyodide CDN shall be bundled when serve_all_deps is True
When `serve_all_deps=True`, pure-Python packages available in the Pyodide CDN SHALL be bundled into the app wheel. This replaces the previous behavior where they were neither bundled nor loaded from the CDN, making them unavailable in the browser.

#### Scenario: Pure-Python CDN package with serve_all_deps=True
- **WHEN** `AppConfig(dependencies=["httpx"], serve_all_deps=True)` and `httpx` is a pure-Python package in the Pyodide CDN
- **THEN** `httpx` SHALL be downloaded from the Pyodide CDN at build time
- **AND** `httpx` SHALL be bundled into the app wheel
- **AND** `httpx` SHALL NOT appear in `py-config.packages`

#### Scenario: Pure-Python CDN package with serve_all_deps=False
- **WHEN** `AppConfig(dependencies=["httpx"], serve_all_deps=False)` and `httpx` is a pure-Python package in the Pyodide CDN
- **THEN** `httpx` SHALL NOT be bundled into the app wheel
- **AND** `httpx` SHALL appear in `py-config.packages` as a plain package name

### Requirement: Only WASM packages shall be loaded from the Pyodide CDN by name; pure-Python CDN package handling depends on serve_all_deps
Only WASM packages are always loaded from the Pyodide CDN by name via `py-config.packages`. Pure-Python packages available in the Pyodide CDN are either bundled (when `serve_all_deps=True`) or loaded from the CDN by name (when `serve_all_deps=False`).

#### Scenario: WASM package (regardless of serve_all_deps)
- **WHEN** a dependency is a WASM package in the Pyodide CDN
- **THEN** it SHALL always be loaded from the CDN by name via `py-config.packages`
- **AND** it SHALL NOT be bundled