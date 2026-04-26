# Lock File — Delta: feat-lockfile-sync

## ADDED Requirements

### Requirement: The lock file shall support exporting dependency versions to requirements.txt
`webcompy lock --export-requirements` SHALL generate a `requirements.txt` file containing pinned version entries for all packages that require local installation. Only packages in `bundled_packages` and non-WASM `pyodide_packages` SHALL be included. WASM-only `pyodide_packages` SHALL be excluded because they are loaded from the Pyodide CDN and not needed locally.

#### Scenario: Exporting requirements from lock file
- **WHEN** a developer runs `webcompy lock --export-requirements`
- **AND** the lock file contains `bundled_packages` with `markupsafe` version `2.1.5` and `click` version `8.1.7`
- **AND** the lock file contains `pyodide_packages` with `numpy` (`is_wasm=True`) and `jinja2` (`is_wasm=False`, version `3.1.6`)
- **THEN** a `requirements.txt` file SHALL be created in the current working directory
- **AND** it SHALL contain `markupsafe==2.1.5`, `click==8.1.7`, and `jinja2==3.1.6`
- **AND** it SHALL NOT contain `numpy` (WASM packages are excluded)

#### Scenario: Exporting requirements to a custom path
- **WHEN** a developer runs `webcompy lock --export-requirements --path deps/requirements.txt`
- **THEN** the requirements file SHALL be written to the specified path
- **AND** parent directories SHALL be created if they do not exist

#### Scenario: Exporting requirements with no lock file
- **WHEN** a developer runs `webcompy lock --export-requirements` without an existing lock file
- **THEN** an error SHALL be reported indicating that the lock file must be generated first

### Requirement: The lock file shall support comparison with external dependency specifications
`webcompy lock --sync-from <source>` SHALL read version information from an external file and compare it with the lock file. The command SHALL report matching versions, mismatches, and missing entries without modifying the lock file.

#### Scenario: Sync from requirements.txt with matching versions
- **WHEN** a developer runs `webcompy lock --sync-from requirements.txt`
- **AND** all entries in `requirements.txt` match the versions in `webcompy-lock.json`
- **THEN** the command SHALL report that all versions match

#### Scenario: Sync from requirements.txt with version mismatches
- **WHEN** a developer runs `webcompy lock --sync-from requirements.txt`
- **AND** `requirements.txt` has `markupsafe==3.0.2` but the lock file has `markupsafe` version `2.1.5`
- **THEN** the command SHALL report the mismatch (lock file: `2.1.5`, requirements.txt: `3.0.2`)
- **AND** the command SHALL suggest installing the lock file version (`pip install markupsafe==2.1.5`)

#### Scenario: Sync from requirements.txt with extra entries
- **WHEN** a developer runs `webcompy lock --sync-from requirements.txt`
- **AND** `requirements.txt` contains a package not present in the lock file
- **THEN** the command SHALL report the extra entry as informational (it may be a non-browser dependency)

#### Scenario: Sync from pyproject.toml
- **WHEN** a developer runs `webcompy lock --sync-from pyproject.toml`
- **AND** the `[project.dependencies]` section contains `markupsafe==2.1.5`
- **AND** the lock file has `markupsafe` version `2.1.5`
- **THEN** the command SHALL report that the version matches

#### Scenario: Sync from pyproject.toml with version ranges
- **WHEN** a developer runs `webcompy lock --sync-from pyproject.toml`
- **AND** the `[project.dependencies]` section contains `requests>=2.31` (not pinned)
- **THEN** the command SHALL report that the dependency is not pinned
- **AND** the command SHALL suggest pinning it to the lock file version (e.g., `requests==2.32.4`)

#### Scenario: Sync from non-existent file
- **WHEN** a developer runs `webcompy lock --sync-from nonexistent.txt`
- **THEN** an error SHALL be reported indicating the file was not found

### Requirement: The lock file shall support installing dependencies from the lock file
`webcompy lock --install` SHALL export the lock file dependencies to a temporary `requirements.txt` and run `pip install -r` to install matching versions locally.

#### Scenario: Installing dependencies from lock file
- **WHEN** a developer runs `webcompy lock --install`
- **THEN** a `requirements.txt` SHALL be generated (as per `--export-requirements`)
- **AND** `pip install -r requirements.txt` SHALL be executed
- **AND** the exit code of `pip install` SHALL be propagated

#### Scenario: Installing dependencies with custom path
- **WHEN** a developer runs `webcompy lock --install --path deps/requirements.txt`
- **THEN** the requirements file SHALL be written to the specified path
- **AND** `pip install -r deps/requirements.txt` SHALL be executed

#### Scenario: Install with no lock file
- **WHEN** a developer runs `webcompy lock --install` without an existing lock file
- **THEN** an error SHALL be reported indicating that the lock file must be generated first

### Requirement: Export/import CLI flags shall be mutually exclusive with default lock generation
The `--export-requirements`, `--sync-from`, and `--install` flags SHALL be mutually exclusive. Each flag controls a distinct operation: default lock generation, export, sync comparison, or install.

#### Scenario: Using --export-requirements
- **WHEN** a developer runs `webcompy lock --export-requirements`
- **THEN** only the export operation SHALL be performed
- **AND** the lock file SHALL NOT be regenerated

#### Scenario: Using --install
- **WHEN** a developer runs `webcompy lock --install`
- **THEN** only the install operation SHALL be performed
- **AND** the lock file SHALL NOT be regenerated

#### Scenario: Combining mutually exclusive flags
- **WHEN** a developer runs `webcompy lock --export-requirements --install`
- **THEN** an error SHALL be reported indicating that the flags are mutually exclusive
