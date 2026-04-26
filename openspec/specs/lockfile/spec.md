# Lock File

## Purpose

The lock file (`webcompy-lock.json`) ensures reproducible builds by recording the exact dependency classifications, versions, and sources used for browser deployment. It serves a similar role to `uv.lock` or `poetry.lock` — pinning the dependency graph so that all environments produce consistent output.

## Requirements

### Requirement: The lock file shall record dependency classification for reproducible builds
`webcompy-lock.json` SHALL be a JSON file placed in the app package directory (next to `webcompy_config.py`) that records Pyodide CDN package versions, bundled package versions and sources, and the Pyodide/PyScript versions used. The lock file SHALL be version-controlled (like `uv.lock` or `poetry.lock`). The `bundled_packages` entries include an `is_pure_python` field that is informational — it records the classification result for human readability and debugging, but is not used during the resolution flow. Additional keys (e.g., `standalone_assets`) may be added by other changes.

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
- **THEN** the lock file SHALL record it in `pyodide_packages` with `version` (from the Pyodide lock), `file_name` from the Pyodide lock, `is_wasm=false`, and `source` (`"explicit"` or `"transitive"`)
- **AND** the package SHALL NOT appear in `py-config.packages`

#### Scenario: Bundled package entry
- **WHEN** a dependency is classified as `bundled`
- **THEN** the lock file SHALL record it in `bundled_packages` with `version`, `source` (`"explicit"` or `"transitive"`), and `is_pure_python` (boolean)

### Requirement: The lock file shall be validated against current dependencies
When loading an existing lock file, the CLI SHALL validate that `AppConfig.dependencies` matches the union of `explicit` entries in `bundled_packages` and `explicit` entries in `pyodide_packages`. If dependencies have changed, the lock file SHALL be regenerated. Additionally, the CLI SHALL validate that the local environment provides the packages recorded in the lock file with matching versions and correct purity classification.

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

#### Scenario: Bundled package version mismatch
- **WHEN** a pure-Python package listed in `bundled_packages` has version `X.Y.Z` in the lock file, but `importlib.metadata.version()` reports a different version
- **THEN** an error SHALL be reported indicating the version mismatch (lock file version vs. local version)
- **AND** the error SHALL suggest installing the lock file version (e.g., `pip install <package>==X.Y.Z`)
- **AND** the build SHALL fail

#### Scenario: Bundled package version unknown locally
- **WHEN** a pure-Python package listed in `bundled_packages` is found locally via `importlib.util.find_spec()`, but `importlib.metadata.version()` returns `None` (version cannot be determined)
- **THEN** an error SHALL be reported indicating the version could not be determined locally
- **AND** the error SHALL include the lock file version requirement
- **AND** the build SHALL fail

#### Scenario: Non-WASM Pyodide CDN package version mismatch
- **WHEN** a non-WASM Pyodide CDN package listed in `pyodide_packages` has a version in the lock file that differs from the locally installed version
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

### Requirement: The lock file shall support exporting dependency versions to requirements.txt
`webcompy lock --export` SHALL generate a `requirements.txt` file containing pinned version entries for all packages that require local installation. Only packages in `bundled_packages` and non-WASM `pyodide_packages` SHALL be included. WASM-only `pyodide_packages` SHALL be excluded because they are loaded from the Pyodide CDN and not needed locally. WebComPy is an SSR/SSG framework — all non-WASM packages are required locally for server-side rendering.

#### Scenario: Exporting requirements from lock file
- **WHEN** a developer runs `webcompy lock --export`
- **AND** the lock file contains `bundled_packages` with `markupsafe` version `2.1.5` and `click` version `8.1.7`
- **AND** the lock file contains `pyodide_packages` with `numpy` (`is_wasm=True`) and `jinja2` (`is_wasm=False`, version `3.1.6`)
- **THEN** a `requirements.txt` file SHALL be generated at the auto-discovered project root
- **AND** it SHALL contain `markupsafe==2.1.5`, `click==8.1.7`, and `jinja2==3.1.6`
- **AND** it SHALL NOT contain `numpy` (WASM packages are excluded)

#### Scenario: Exporting requirements when project root is auto-discovered
- **WHEN** a developer runs `webcompy lock --export`
- **AND** `LockfileSyncConfig.requirements_path` is not set
- **THEN** the project root SHALL be discovered by walking up from `app_package_path` until a directory containing `pyproject.toml` is found
- **AND** the `requirements.txt` file SHALL be written to the project root directory

#### Scenario: Exporting requirements with explicit path configuration
- **WHEN** a developer has `LockfileSyncConfig(requirements_path="../requirements.txt")` in `webcompy_server_config.py`
- **THEN** the requirements file SHALL be written to the path resolved relative to `app_package_path`
- **AND** auto-discovery SHALL be skipped

#### Scenario: Exporting requirements with no pyproject.toml found
- **WHEN** a developer runs `webcompy lock --export`
- **AND** `LockfileSyncConfig.requirements_path` is not set
- **AND** no `pyproject.toml` is found above `app_package_path`
- **THEN** an error SHALL be reported instructing the developer to set `LockfileSyncConfig.requirements_path` in `webcompy_server_config.py`

#### Scenario: Exporting requirements with no lock file
- **WHEN** a developer runs `webcompy lock --export` without an existing lock file
- **THEN** an error SHALL be reported indicating that the lock file must be generated first by running `webcompy lock`

### Requirement: The lock file shall support comparison with external dependency specifications
`webcompy lock --sync` SHALL auto-discover `requirements.txt` and `pyproject.toml` at the project root and compare their dependency entries with the lock file. The command SHALL report matching versions, mismatches, and missing entries without modifying the lock file.

#### Scenario: Sync from requirements.txt with matching versions
- **WHEN** a developer runs `webcompy lock --sync`
- **AND** `requirements.txt` exists at the project root
- **AND** all entries in `requirements.txt` match the versions in `webcompy-lock.json`
- **THEN** the command SHALL report that all versions match

#### Scenario: Sync from requirements.txt with version mismatches
- **WHEN** a developer runs `webcompy lock --sync`
- **AND** `requirements.txt` has `markupsafe==3.0.2` but the lock file has `markupsafe` version `2.1.5`
- **THEN** the command SHALL report the mismatch (lock file: `2.1.5`, requirements.txt: `3.0.2`)
- **AND** the command SHALL suggest installing the lock file version (`pip install markupsafe==2.1.5`)

#### Scenario: Sync from requirements.txt with extra entries
- **WHEN** a developer runs `webcompy lock --sync`
- **AND** `requirements.txt` contains a package not present in the lock file
- **THEN** the command SHALL report the extra entry as informational (it may be a non-browser dependency)

#### Scenario: Sync from pyproject.toml with sync_group
- **WHEN** a developer runs `webcompy lock --sync`
- **AND** `LockfileSyncConfig(sync_group="browser")` is set
- **AND** the `pyproject.toml` contains `[project.optional-dependencies]` with a `browser` key
- **THEN** the command SHALL compare `[project.optional-dependencies.browser]` entries against the lock file
- **AND** the command SHALL NOT compare `[project.dependencies]` entries

#### Scenario: Sync from pyproject.toml without sync_group
- **WHEN** a developer runs `webcompy lock --sync`
- **AND** `LockfileSyncConfig.sync_group` is `None` (default)
- **THEN** the command SHALL compare `[project.dependencies]` entries against the lock file

#### Scenario: Sync from pyproject.toml with version ranges
- **WHEN** a developer runs `webcompy lock --sync`
- **AND** `[project.dependencies]` contains `requests>=2.31` (not pinned)
- **THEN** the command SHALL report that the dependency is not pinned
- **AND** the command SHALL suggest pinning it to the lock file version (e.g., `requests==2.32.4`)

#### Scenario: Sync with both requirements.txt and pyproject.toml
- **WHEN** a developer runs `webcompy lock --sync`
- **AND** both `requirements.txt` and `pyproject.toml` exist at the project root
- **THEN** the command SHALL compare against both sources
- **AND** the command SHALL report results from each source separately

### Requirement: The lock file shall support installing dependencies from the lock file
`webcompy lock --install` SHALL export the lock file dependencies to `requirements.txt` (via auto-discovery) and run a package manager to install matching versions locally.

#### Scenario: Installing dependencies from lock file with uv available
- **WHEN** a developer runs `webcompy lock --install`
- **AND** `uv` is available in the system PATH
- **THEN** a `requirements.txt` SHALL be generated via auto-discovery
- **AND** `uv pip install -r {path}` SHALL be executed
- **AND** the exit code of `uv pip install` SHALL be propagated

#### Scenario: Installing dependencies with pip fallback
- **WHEN** a developer runs `webcompy lock --install`
- **AND** `uv` is not available in the system PATH
- **THEN** `sys.executable -m pip install -r {path}` SHALL be executed
- **AND** the exit code of `pip install` SHALL be propagated

#### Scenario: Install with no lock file
- **WHEN** a developer runs `webcompy lock --install` without an existing lock file
- **THEN** an error SHALL be reported indicating that the lock file must be generated first

### Requirement: Project root discovery shall use pyproject.toml as boundary
The lock file sync commands SHALL discover the project root by walking up from `app_package_path` until a directory containing `pyproject.toml` is found. This directory is the project root. If `pyproject.toml` is not found, an error SHALL be reported. When `LockfileSyncConfig.requirements_path` is set, auto-discovery SHALL be skipped and the explicit path SHALL be used.

#### Scenario: Project root found via pyproject.toml
- **WHEN** `app_package_path` is `/home/user/project/my_app/`
- **AND** `/home/user/project/pyproject.toml` exists
- **THEN** the project root SHALL be `/home/user/project/`
- **AND** `requirements.txt` and `pyproject.toml` SHALL be searched in that directory

#### Scenario: Project root not found
- **WHEN** no `pyproject.toml` is found above `app_package_path`
- **THEN** an error SHALL be reported instructing the developer to set `LockfileSyncConfig.requirements_path`

#### Scenario: Explicit path overrides auto-discovery
- **WHEN** `LockfileSyncConfig(requirements_path="../requirements.txt")` is set
- **THEN** the path SHALL be resolved relative to `app_package_path`
- **AND** no upward directory walk SHALL be performed

### Requirement: Discovered paths shall be recorded in LockfileSyncConfig
When auto-discovery finds a project root, the discovered `requirements_path` SHALL be written to `LockfileSyncConfig` in `webcompy_server_config.py` so that subsequent invocations skip the discovery step.

#### Scenario: Recording discovered path
- **WHEN** a developer runs `webcompy lock --export` for the first time
- **AND** `LockfileSyncConfig.requirements_path` is not set
- **AND** auto-discovery finds `pyproject.toml` at `/home/user/project/`
- **THEN** `LockfileSyncConfig.requirements_path` SHALL be set to a relative path from `app_package_path` to the discovered `requirements.txt` location
- **AND** the value SHALL be written to `webcompy_server_config.py`

#### Scenario: Using recorded path on subsequent runs
- **WHEN** a developer runs `webcompy lock --export` again
- **AND** `LockfileSyncConfig.requirements_path` is already set
- **THEN** the recorded path SHALL be used without re-running discovery