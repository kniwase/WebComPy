# Lock File

## Purpose

The lock file (`webcompy-lock.json`) ensures reproducible builds by recording the exact dependency classifications, versions, and sources used for browser deployment. It serves a similar role to `uv.lock` or `poetry.lock` — pinning the dependency graph so that all environments produce consistent output.

## Requirements

### Requirement: The lock file shall use v2 schema with wasm_packages and pure_python_packages
The lock file SHALL use schema version 2, which replaces `pyodide_packages` with `wasm_packages` and `bundled_packages` with `pure_python_packages`. Version 1 lock files SHALL be treated as invalid (returning `None` from `load_lockfile()`), triggering full regeneration. `webcompy-lock.json` SHALL be a JSON file placed in the app package directory (next to `webcompy_config.py`) that records WASM package versions, pure-Python package versions and CDN metadata, and the Pyodide/PyScript versions used. The lock file SHALL be version-controlled (like `uv.lock` or `poetry.lock`). CDN-available pure-Python package entries include `in_pyodide_cdn`, `pyodide_file_name`, and `pyodide_sha256` fields. Additional keys (e.g., `standalone_assets`) may be added by other changes. Population of `wasm_packages` and `pure_python_packages` SHALL be determined by `PackageKind` from `classify_dependencies()`: `PackageKind.WASM` entries go to `wasm_packages`, `PackageKind.CDN_PURE_PYTHON` and `PackageKind.LOCAL_PURE_PYTHON` entries go to `pure_python_packages`.

#### Scenario: Lock file generated on first run
- **WHEN** a developer runs `webcompy start` or `webcompy generate` without an existing lock file
- **THEN** the lock file SHALL be automatically generated and saved
- **AND** the developer SHOULD commit the lock file to version control

#### Scenario: v2 lock file schema
- **WHEN** a lock file is generated
- **THEN** it SHALL contain `version: 2`, `pyodide_version`, `pyscript_version`, `wasm_packages`, and `pure_python_packages`

#### Scenario: v1 lock file rejection
- **WHEN** `load_lockfile()` encounters a lock file with `version: 1`
- **THEN** it SHALL return `None`
- **AND** the build system SHALL regenerate the lock file

### Requirement: wasm_packages shall contain only WASM packages
`wasm_packages` SHALL contain only WASM packages that must be loaded from the Pyodide CDN by name via `py-config.packages`. Pure-Python packages available in the Pyodide CDN SHALL NOT appear in `wasm_packages`.

#### Scenario: WASM package entry in v2 lock file
- **WHEN** a dependency `numpy` is a WASM package
- **THEN** it SHALL be recorded in `wasm_packages` with `version`, `file_name`, and `source`

#### Scenario: Pure-Python CDN package not in wasm_packages
- **WHEN** a dependency `httpx` is a pure-Python package in the Pyodide CDN
- **THEN** it SHALL NOT appear in `wasm_packages`
- **AND** it SHALL appear in `pure_python_packages`

### Requirement: pure_python_packages shall contain all pure-Python packages with CDN metadata
`pure_python_packages` SHALL contain all pure-Python dependencies regardless of CDN availability. Entries for CDN-available packages SHALL include `in_pyodide_cdn: true` with `pyodide_file_name` and `pyodide_sha256` for download. Entries for local-only packages SHALL have `in_pyodide_cdn: false`.

#### Scenario: CDN-available pure-Python package entry
- **WHEN** a pure-Python package `httpx` is available in the Pyodide CDN
- **THEN** the entry SHALL include `in_pyodide_cdn: true`, `pyodide_file_name: "httpx-0.28.1-py3-none-any.whl"`, and `pyodide_sha256`
- **AND** `serve_all_deps=True` SHALL cause this package to be downloaded at build time

#### Scenario: Local-only pure-Python package entry
- **WHEN** a pure-Python package `flask` is NOT available in the Pyodide CDN
- **THEN** the entry SHALL include `in_pyodide_cdn: false`
- **AND** it SHALL NOT have `pyodide_file_name` or `pyodide_sha256`
- **AND** this package SHALL always be bundled from local installation

#### Scenario: Pure-Python CDN package is bundled when serve_all_deps=True
- **WHEN** `serve_all_deps=True` and a pure-Python package has `in_pyodide_cdn: true`
- **THEN** the build system SHALL download the wheel, verify SHA256, extract, and bundle it

#### Scenario: Pure-Python CDN package is loaded from CDN when serve_all_deps=False
- **WHEN** `serve_all_deps=False` and a pure-Python package has `in_pyodide_cdn: true`
- **THEN** the package name SHALL be included in `py-config.packages` for CDN loading
- **AND** the package SHALL NOT be bundled

### Requirement: The lock file shall be validated against current dependencies
When loading an existing lock file, the CLI SHALL validate that `AppConfig.dependencies` matches the union of `explicit` entries in `pure_python_packages` and `explicit` entries in `wasm_packages`. If dependencies have changed, the lock file SHALL be regenerated. Additionally, the CLI SHALL validate that the local environment provides the packages recorded in the lock file with matching versions.

#### Scenario: Lock file matches dependencies
- **WHEN** the lock file's explicit dependencies match `AppConfig.dependencies`
- **THEN** the lock file SHALL be used as-is

#### Scenario: Lock file is stale
- **WHEN** `AppConfig.dependencies` has been modified since the lock file was generated
- **THEN** the lock file SHALL be regenerated automatically

#### Scenario: Pure-Python package missing from local environment
- **WHEN** a package listed in `pure_python_packages` with `in_pyodide_cdn=false` is not found in the local Python environment via `importlib.util.find_spec()`
- **THEN** an error SHALL be reported with the package name, the lock file version, and a suggestion to install it (e.g., `pip install <package>==<version>`)
- **AND** the build SHALL fail

#### Scenario: CDN-available pure-Python package missing locally with serve_all_deps=True
- **WHEN** a package listed in `pure_python_packages` with `in_pyodide_cdn=true` is not found in the local environment
- **AND** `serve_all_deps=True`
- **THEN** a warning SHALL be reported indicating the package will be downloaded from the Pyodide CDN
- **AND** the build SHALL continue

#### Scenario: Pure-Python package version mismatch
- **WHEN** a pure-Python package listed in `pure_python_packages` has version `X.Y.Z` in the lock file, but `importlib.metadata.version()` reports a different version
- **THEN** an error SHALL be reported indicating the version mismatch (lock file version vs. local version)
- **AND** the error SHALL suggest installing the lock file version (e.g., `pip install <package>==X.Y.Z`)
- **AND** the build SHALL fail

#### Scenario: Pure-Python package version unknown locally
- **WHEN** a pure-Python package listed in `pure_python_packages` is found locally via `importlib.util.find_spec()`, but `importlib.metadata.version()` returns `None` (version cannot be determined)
- **THEN** an error SHALL be reported indicating the version could not be determined locally
- **AND** the error SHALL include the lock file version requirement
- **AND** the build SHALL fail

#### Scenario: CDN-available pure-Python package version mismatch
- **WHEN** a pure-Python package listed in `pure_python_packages` with `in_pyodide_cdn=true` has a version in the lock file that differs from the locally installed version
- **THEN** a warning SHALL be reported indicating the version mismatch
- **AND** the build SHALL continue (the local version will be used for SSR while the CDN version is recorded in the lock file)
- **AND** the warning SHALL note that the local version will be used for SSR/SSG

#### Scenario: WASM package not locally installed
- **WHEN** a package listed in `wasm_packages` is not found in the local environment
- **THEN** a warning SHALL be reported indicating the package is needed locally for SSR/SSG
- **AND** the build SHALL continue

#### Scenario: WASM package version mismatch
- **WHEN** a WASM package listed in `wasm_packages` has a version in the lock file that differs from the locally installed version
- **THEN** a warning SHALL be reported indicating the version mismatch
- **AND** the build SHALL continue (the local version will be used for SSR/SSG)
- **AND** the warning SHALL note that the local version will be used for SSR/SSG

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

### Requirement: The lock file shall support querying CDN-available pure-Python package names
`get_cdn_pure_python_package_names(lockfile)` SHALL return the names of pure-Python packages with `in_pyodide_cdn=True`. This is used when `serve_all_deps=False` to generate the `py-config.packages` list.

#### Scenario: Querying CDN pure-Python names
- **WHEN** a lock file contains `pure_python_packages` with `httpx (in_pyodide_cdn=true)` and `flask (in_pyodide_cdn=false)`
- **THEN** `get_cdn_pure_python_package_names()` SHALL return `["httpx"]`

### Requirement: export_requirements shall include all packages from v2 lock file
`export_requirements()` SHALL write a `requirements.txt` containing pinned versions for all packages in `pure_python_packages` and `wasm_packages`. The v2 schema no longer uses an `is_wasm` flag; all packages are included because the developer may need them locally for SSR/SSG. This replaces the v1 behavior where WASM-only `pyodide_packages` were excluded.

#### Scenario: Exporting all packages from v2 lock file
- **WHEN** a developer runs `webcompy lock --export`
- **AND** the v2 lock file contains `wasm_packages` with `numpy` and `pure_python_packages` with `httpx` and `flask`
- **THEN** `requirements.txt` SHALL contain `numpy==<version>`, `httpx==<version>`, and `flask==<version>`

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

### Requirement: get_bundled_deps shall consider serve_all_deps
`get_bundled_deps(lockfile, serve_all_deps=True)` SHALL return pure-Python packages to be bundled from local installation. CDN-available packages are handled separately via the download pipeline and are NEVER returned by `get_bundled_deps()`.

#### Scenario: get_bundled_deps with serve_all_deps=True
- **WHEN** `serve_all_deps=True`
- **THEN** `get_bundled_deps()` SHALL return only `pure_python_packages` entries with `in_pyodide_cdn=False` that have local `pkg_dir` available
- **AND** CDN packages to be downloaded are handled separately via the download pipeline

#### Scenario: get_bundled_deps with serve_all_deps=False
- **WHEN** `serve_all_deps=False`
- **THEN** `get_bundled_deps()` SHALL return only `pure_python_packages` entries with `in_pyodide_cdn=False`

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

### Requirement: The lock file shall record the WASM serving mode and local asset metadata
`webcompy-lock.json` SHALL include a `wasm_serving` field indicating whether WASM packages are served from CDN or locally. When `wasm_serving="local"`, WASM package entries in `wasm_packages` SHALL include their Pyodide CDN download URL and SHA256 hash for build-time verification.

#### Scenario: Lock file with local WASM serving
- **WHEN** a lock file is generated with `wasm_serving="local"`
- **THEN** the lock file SHALL contain `"wasm_serving": "local"`
- **AND** each entry in `wasm_packages` SHALL include `file_name` and `sha256` fields for download verification

#### Scenario: Lock file with CDN WASM serving (default)
- **WHEN** a lock file is generated with `wasm_serving="cdn"` (default)
- **THEN** the lock file SHALL contain `"wasm_serving": "cdn"`
- **AND** WASM package entries SHALL include `file_name` for reference but download verification is not required at build time

### Requirement: The lock file shall record the runtime serving mode
`webcompy-lock.json` SHALL include a `runtime_serving` field indicating whether PyScript/Pyodide runtime assets are served from CDN or locally.

#### Scenario: Lock file with local runtime serving
- **WHEN** a lock file is generated with `runtime_serving="local"`
- **THEN** the lock file SHALL contain `"runtime_serving": "local"`
- **AND** the lock file SHALL include a `runtime_assets` section

#### Scenario: Lock file with CDN runtime serving (default)
- **WHEN** a lock file is generated with `runtime_serving="cdn"` (default)
- **THEN** the lock file SHALL contain `"runtime_serving": "cdn"`
- **AND** the `runtime_assets` section SHALL NOT be present

### Requirement: The lock file shall include runtime asset metadata when runtime_serving is local
When `runtime_serving="local"`, `webcompy-lock.json` SHALL include a `runtime_assets` section recording the download URLs of PyScript and Pyodide runtime files. SHA256 hashes are populated after the first build: `webcompy lock` records URLs only (with `sha256: null`), and the first `webcompy start` or `webcompy generate` computes and writes SHA256 hashes to the lock file. Subsequent builds verify downloaded files against these recorded hashes.

#### Scenario: Runtime assets section after lock generation
- **WHEN** a lock file is generated with `webcompy lock` and `runtime_serving="local"`
- **THEN** the `runtime_assets` section SHALL contain entries for `core.js`, `core.css`, `pyodide.mjs`, `pyodide.asm.wasm`, `pyodide.asm.js`, `python_stdlib.zip`, and `pyodide-lock.json`
- **AND** each entry SHALL include the download `url`
- **AND** each entry's `sha256` SHALL be `null` (not yet computed)

#### Scenario: Runtime assets section after first build
- **WHEN** a build (`webcompy start` or `webcompy generate`) runs with `runtime_serving="local"` and downloads runtime assets
- **THEN** each `runtime_assets` entry SHALL be updated with the computed `sha256` hash
- **AND** the lock file SHALL be re-saved with the computed hashes

#### Scenario: SHA256 verification on subsequent builds
- **WHEN** a build runs with `runtime_serving="local"` and the lock file already contains `runtime_assets` with `sha256` hashes
- **THEN** each downloaded file's SHA256 SHALL be verified against the recorded hash
- **AND** a mismatch SHALL raise a `RuntimeDownloadError`

#### Scenario: Runtime assets absent in CDN mode
- **WHEN** a lock file is generated with `runtime_serving="cdn"`
- **THEN** the `runtime_assets` section SHALL NOT be present