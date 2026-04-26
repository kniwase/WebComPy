# Lock File — Delta: feat-lockfile-sync

## MODIFIED Requirements

### Requirement: Dependencies shall be classified via lock file resolution
(Modifies existing requirement in `openspec/specs/cli/spec.md`)

When `AppConfig.dependencies` is `None`, the CLI SHALL auto-populate it from `pyproject.toml` before lock file generation. The resolution uses `AppConfig.dependencies_from` to determine which section of `pyproject.toml` to read. Version specifiers in `pyproject.toml` entries (e.g., `"flask>=3.0"`, `"numpy==2.2.5"`) SHALL be stripped before classification — only package names are used in `AppConfig.dependencies`; version pinning is handled by the lock file.

#### Scenario: Auto-populated dependencies from pyproject.toml
- **WHEN** `AppConfig(dependencies=None, dependencies_from="browser")` and `pyproject.toml` has `[project.optional-dependencies] browser = ["numpy", "matplotlib"]`
- **THEN** dependencies SHALL be resolved to `["numpy", "matplotlib"]` before lock file generation
- **AND** the lock file SHALL be generated as if `dependencies=["numpy", "matplotlib"]` were explicitly set

#### Scenario: Version specifiers are stripped
- **WHEN** `pyproject.toml` has `dependencies = ["flask>=3.0", "click==8.1.7"]`
- **THEN** `AppConfig.dependencies` SHALL be set to `["flask", "click"]` (no version specifiers)

#### Scenario: Explicit dependencies bypass auto-population
- **WHEN** `AppConfig(dependencies=["numpy"])` (explicit list, not None)
- **THEN** no `pyproject.toml` reading SHALL occur
- **AND** `["numpy"]` SHALL be used as-is

## ADDED Requirements

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