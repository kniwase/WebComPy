# Lock File — Delta: feat-wheel-split

## ADDED Requirements

### Requirement: The lock file shall record dependency classification for reproducible builds
`webcompy-lock.json` SHALL be a JSON file placed in the project root (next to `webcompy_config.py`) that records Pyodide CDN package versions, bundled package versions and sources, and the Pyodide/PyScript versions used. The lock file SHALL be version-controlled (like `uv.lock` or `poetry.lock`).

#### Scenario: Lock file schema
- **WHEN** a lock file is generated
- **THEN** it SHALL contain `version` (integer), `pyodide_version` (string), `pyscript_version` (string), `pyodide_packages` (object mapping package names to version and file_name), and `bundled_packages` (object mapping package names to version, source, and is_pure_python)
- **AND** `version` SHALL be `1`

#### Scenario: Pyodide CDN package entry
- **WHEN** a dependency is classified as `pyodide_cdn`
- **THEN** the lock file SHALL record it in `pyodide_packages` with `version` and `file_name` from the Pyodide lock

#### Scenario: Bundled package entry
- **WHEN** a dependency is classified as `bundled`
- **THEN** the lock file SHALL record it in `bundled_packages` with `version` (from local `importlib.metadata`), `source` (`"explicit"` or `"transitive"`), and `is_pure_python` (boolean)

### Requirement: The lock file shall be validated against current dependencies
When loading an existing lock file, the CLI SHALL validate that `AppConfig.dependencies` matches the `explicit` entries in `bundled_packages` plus all entries in `pyodide_packages`. If dependencies have changed, the lock file SHALL be regenerated.

#### Scenario: Lock file matches dependencies
- **WHEN** the lock file's explicit dependencies match `AppConfig.dependencies`
- **THEN** the lock file SHALL be used as-is

#### Scenario: Lock file is stale
- **WHEN** `AppConfig.dependencies` has been modified since the lock file was generated
- **THEN** the lock file SHALL be regenerated automatically

### Requirement: The lock file position shall be next to the app package
The lock file SHALL be stored at `app_package_path.parent / "webcompy-lock.json"`, which is the project root directory containing `webcompy_config.py`.

#### Scenario: Finding the lock file path
- **WHEN** the app package is at `/project/myapp/`
- **THEN** the lock file path SHALL be `/project/webcompy-lock.json`