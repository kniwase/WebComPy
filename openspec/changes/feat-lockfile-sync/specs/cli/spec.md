# CLI — Delta: feat-lockfile-sync

## ADDED Requirements

### Requirement: The `webcompy lock` command shall support dependency export, sync, and install operations
The `webcompy lock` command SHALL support three additional operations beyond default lock file generation: `--export`, `--sync`, and `--install`. These operations enable synchronization between the WebComPy lock file and external Python package management tools. All three operations use auto-discovery to locate `requirements.txt` and `pyproject.toml` at the project root.

#### Scenario: Running `webcompy lock --export`
- **WHEN** a developer runs `webcompy lock --export`
- **THEN** a `requirements.txt` file SHALL be generated at the auto-discovered project root containing pinned versions for all locally-required packages from the lock file
- **AND** the lock file SHALL NOT be regenerated

#### Scenario: Running `webcompy lock --sync`
- **WHEN** a developer runs `webcompy lock --sync`
- **THEN** the command SHALL auto-discover `requirements.txt` and `pyproject.toml` at the project root
- **AND** compare the pinned versions against the lock file
- **AND** report matching versions, mismatches, and extra entries
- **AND** SHALL NOT modify the lock file

#### Scenario: Running `webcompy lock --install`
- **WHEN** a developer runs `webcompy lock --install`
- **THEN** a `requirements.txt` file SHALL be generated from the lock file via auto-discovery
- **AND** `uv pip install -r {path}` SHALL be executed if `uv` is available, otherwise `sys.executable -m pip install -r {path}`
- **AND** the exit code of the install command SHALL be the exit code of the `webcompy lock --install` command

#### Scenario: Combining mutually exclusive flags
- **WHEN** a developer runs `webcompy lock` with both `--export` and `--install`
- **THEN** an error SHALL be reported indicating that the operations are mutually exclusive

#### Scenario: Running `webcompy lock --export` without a lock file
- **WHEN** a developer runs `webcompy lock --export` without an existing `webcompy-lock.json`
- **THEN** an error SHALL be reported indicating that the lock file must be generated first by running `webcompy lock`

#### Scenario: Running `webcompy lock --sync` with sync_group configuration
- **WHEN** a developer has `LockfileSyncConfig(sync_group="browser")` in `webcompy_server_config.py`
- **AND** runs `webcompy lock --sync`
- **THEN** the command SHALL compare `[project.optional-dependencies.browser]` from `pyproject.toml` against the lock file

#### Scenario: Default `webcompy lock` unchanged
- **WHEN** a developer runs `webcompy lock` without any flags
- **THEN** the lock file SHALL be generated or updated (existing behavior preserved)