# Lock File — Delta: feat-dependency-bundling

## ADDED Requirements

### Requirement: The lock file shall record dependency classification for reproducible builds
`webcompy-lock.json` SHALL be a JSON file placed in the project root (next to `webcompy_config.py`) that records Pyodide CDN package versions, bundled package versions and sources, and the Pyodide/PyScript versions used. The lock file SHALL be version-controlled (like `uv.lock` or `poetry.lock`). The `bundled_packages` entries include an `is_pure_python` field that is informational — it records the classification result for human readability and debugging, but is not used during the resolution flow. Additional keys (e.g., `standalone_assets`) may be added by other changes.

#### Scenario: Lock file generated on first run
- **WHEN** a developer runs `webcompy start` or `webcompy generate` without an existing lock file
- **THEN** the lock file SHALL be automatically generated and saved
- **AND** the developer SHOULD commit the lock file to version control

#### Scenario: Lock file schema
- **WHEN** a lock file is generated
- **THEN** it SHALL contain `version` (integer), `pyodide_version` (string), `pyscript_version` (string), `pyodide_packages` (object mapping package names to version, file_name, is_wasm, and source), and `bundled_packages` (object mapping package names to version, source, and is_pure_python)
- **AND** `version` SHALL be `1`

#### Scenario: Pyodide CDN WASM package entry
- **WHEN** a dependency is classified as `pyodide_cdn` and is a WASM package
- **THEN** the lock file SHALL record it in `pyodide_packages` with `version`, `file_name` from the Pyodide lock, `is_wasm=true`, and `source` (`"explicit"` or `"transitive"`)
- **AND** the package SHALL appear in `py-config.packages` for Pyodide CDN loading

#### Scenario: Pyodide CDN pure-Python package entry
- **WHEN** a dependency is classified as `pyodide_cdn` and is a pure-Python package (not WASM)
- **THEN** the lock file SHALL record it in `bundled_packages` with `version` (from the Pyodide lock), `source` (`"explicit"` or `"transitive"`), and `is_pure_python=true`
- **AND** the package SHALL NOT appear in `pyodide_packages` (it is bundled locally, not served from CDN)
- **AND** the package SHALL NOT appear in `py-config.packages`

#### Scenario: WASM package
- **WHEN** a Pyodide CDN package has a `file_name` containing `pyodide` or `wasm32`
- **THEN** `is_wasm` SHALL be `true`
- **AND** the package MUST be loaded from the Pyodide CDN (it cannot be bundled as pure Python)

#### Scenario: Pure Python package in Pyodide CDN
- **WHEN** a Pyodide CDN package has a `file_name` matching `*py3-none-any.whl`
- **THEN** `is_wasm` SHALL be `false`
- **AND** the package SHALL be bundled and served from the WebComPy server
- **AND** the package SHALL NOT appear in `py-config.packages`

#### Scenario: Fallback CDN package (Pyodide lock unavailable)
- **WHEN** the Pyodide lock cannot be fetched and a dependency is not found locally
- **THEN** the package SHALL be recorded in `bundled_packages` with `source="fallback_cdn"`
- **AND** `is_pure_python` SHALL be `true` (assuming pure-Python when local inspection is not possible)
- **AND** the package SHALL appear in `py-config.packages` for micropip resolution

#### Scenario: Bundled package entry
- **WHEN** a dependency is classified as `bundled` or as a pure-Python `pyodide_cdn` package
- **THEN** the lock file SHALL record it in `bundled_packages` with `version`, `source` (`"explicit"`, `"transitive"`, or `"fallback_cdn"`), and `is_pure_python` (boolean)
- **AND** for pure-Python Pyodide CDN packages, the version SHALL come from the Pyodide lock

### Requirement: The lock file shall be validated against current dependencies
When loading an existing lock file, the CLI SHALL validate that `AppConfig.dependencies` matches the `explicit` entries in `bundled_packages` plus all entries in `pyodide_packages`. If dependencies have changed, the lock file SHALL be regenerated. Additionally, the CLI SHALL validate that the local environment provides the packages recorded in the lock file with matching versions and correct purity classification.

#### Scenario: Lock file matches dependencies
- **WHEN** the lock file's explicit dependencies match `AppConfig.dependencies`
- **THEN** the lock file SHALL be used as-is

#### Scenario: Lock file is stale
- **WHEN** `AppConfig.dependencies` has been modified since the lock file was generated
- **THEN** the lock file SHALL be regenerated automatically

#### Scenario: Bundled package missing from local environment
- **WHEN** a package listed in `bundled_packages` is not found in the local Python environment via `importlib.util.find_spec()`
- **THEN** an error SHALL be reported with the package name, the lock file version, and a suggestion to install it (e.g., `pip install <package>==<version>`)
- **AND** the build SHALL fail

#### Scenario: Bundled package version mismatch (locally-installed package)
- **WHEN** a locally-installed package listed in `bundled_packages` with `source` of `"explicit"` or `"transitive"` has version `X.Y.Z` in the lock file, but `importlib.metadata.version()` reports a different version
- **THEN** an error SHALL be reported indicating the version mismatch (lock file version vs. local version)
- **AND** the error SHALL suggest installing the lock file version (e.g., `pip install <package>==X.Y.Z`)
- **AND** the build SHALL fail

#### Scenario: Bundled package version mismatch (Pyodide CDN pure-Python package)
- **WHEN** a pure-Python package from the Pyodide CDN listed in `bundled_packages` has a version in the lock file that differs from the locally installed version
- **THEN** a warning SHALL be reported indicating the version mismatch
- **AND** the build SHALL continue (the local version will be used for SSR while the Pyodide CDN version is recorded in the lock file)
- **AND** the warning SHALL note that the local version will be used for SSR/SSG

#### Scenario: WASM-only Pyodide CDN package not locally installed
- **WHEN** a package listed in `pyodide_packages` with `is_wasm=True` is not found in the local environment
- **THEN** no error or warning SHALL be reported (WASM packages are loaded from the Pyodide CDN in the browser and are not needed for SSR if the app does not import them server-side)

### Requirement: The lock file shall be version-controlled for reproducibility
The lock file SHALL be committed to version control (e.g., git) to ensure reproducible builds across environments. Like `uv.lock` or `poetry.lock`, it records the exact dependency classifications and versions used. Developers SHOULD NOT add `webcompy-lock.json` to `.gitignore`.

#### Scenario: Lock file committed to version control
- **WHEN** a developer generates a lock file via `webcompy lock` or auto-generation
- **THEN** the lock file SHALL be committed to the project repository
- **AND** other developers cloning the repository SHALL get the same dependency classification without re-resolving

#### Scenario: Lock file in CI
- **WHEN** a CI pipeline runs `webcompy generate`
- **AND** the lock file is present in the repository
- **THEN** the lock file SHALL be used as-is (no re-resolution) if `AppConfig.dependencies` has not changed

### Requirement: The lock file position shall be in the app package directory alongside webcompy_config.py
The lock file SHALL be stored at `app_package_path / "webcompy-lock.json"`, which is the same directory containing `webcompy_config.py` and `webcompy_server_config.py`.

#### Scenario: Finding the lock file path
- **WHEN** the app package is at `/project/myapp/` with `webcompy_config.py` at `/project/myapp/webcompy_config.py`
- **THEN** the lock file path SHALL be `/project/myapp/webcompy-lock.json`