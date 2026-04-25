# CLI — Delta: feat-lockfile-sync

## ADDED Requirements

### Requirement: The `webcompy lock` command shall support dependency export, sync, and install operations
The `webcompy lock` command SHALL support three additional operations beyond default lock file generation: `--export-requirements`, `--sync-from <source>`, and `--install`. These operations enable synchronization between the WebComPy lock file and external Python package management tools.

#### Scenario: Running `webcompy lock --export-requirements`
- **WHEN** a developer runs `webcompy lock --export-requirements`
- **THEN** a `requirements.txt` file SHALL be generated in the current working directory containing pinned versions for all locally-required packages from the lock file
- **AND** the lock file SHALL NOT be regenerated

#### Scenario: Running `webcompy lock --export-requirements --path custom.txt`
- **WHEN** a developer runs `webcompy lock --export-requirements --path custom.txt`
- **THEN** the requirements file SHALL be written to the specified path

#### Scenario: Running `webcompy lock --sync-from requirements.txt`
- **WHEN** a developer runs `webcompy lock --sync-from requirements.txt`
- **THEN** the command SHALL compare the pinned versions in `requirements.txt` against the lock file
- **AND** SHALL report matching versions, mismatches, and extra entries
- **AND** SHALL NOT modify the lock file

#### Scenario: Running `webcompy lock --sync-from pyproject.toml`
- **WHEN** a developer runs `webcompy lock --sync-from pyproject.toml`
- **THEN** the command SHALL compare the `[project.dependencies]` entries against the lock file
- **AND** SHALL report matching versions, mismatches, and unpinned dependencies
- **AND** SHALL NOT modify the lock file

#### Scenario: Running `webcompy lock --install`
- **WHEN** a developer runs `webcompy lock --install`
- **THEN** a `requirements.txt` file SHALL be generated from the lock file
- **AND** `pip install -r requirements.txt` SHALL be executed
- **AND** the exit code of `pip install` SHALL be the exit code of the command

#### Scenario: Running `webcompy lock --install --path deps/requirements.txt`
- **WHEN** a developer runs `webcompy lock --install --path deps/requirements.txt`
- **THEN** the requirements file SHALL be written to the specified path
- **AND** `pip install -r deps/requirements.txt` SHALL be executed

#### Scenario: Running `webcompy lock --export-requirements --install`
- **WHEN** a developer runs `webcompy lock` with both `--export-requirements` and `--install`
- **THEN** an error SHALL be reported indicating that the operations are mutually exclusive

#### Scenario: Running `webcompy lock --export-requirements` without a lock file
- **WHEN** a developer runs `webcompy lock --export-requirements` without an existing `webcompy-lock.json`
- **THEN** an error SHALL be reported indicating that the lock file must be generated first by running `webcompy lock`
