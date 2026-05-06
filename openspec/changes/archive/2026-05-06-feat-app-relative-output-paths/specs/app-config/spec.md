## ADDED Requirements

### Requirement: static_files_dir resolution shall be handled by call sites
The `static_files_dir` field in `ServerConfig` and `GenerateConfig` SHALL remain a plain `str` field without a `static_files_dir_path` property. Path resolution SHALL be performed by the CLI call sites (`_generate.py`, `_server.py`) using `(app_package_path / static_files_dir).absolute()`.

#### Scenario: GenerateConfig no longer exposes static_files_dir_path
- **WHEN** code accesses a `GenerateConfig` instance
- **THEN** `GenerateConfig` SHALL have a `static_files_dir: str` field and SHALL NOT have a `static_files_dir_path` property

#### Scenario: ServerConfig no longer exposes static_files_dir_path
- **WHEN** code accesses a `ServerConfig` instance
- **THEN** `ServerConfig` SHALL have a `static_files_dir: str` field and SHALL NOT have a `static_files_dir_path` property

## MODIFIED Requirements

### Requirement: ServerConfig and GenerateConfig shall be internal
`ServerConfig` and `GenerateConfig` SHALL be internal dataclasses used by CLI functions. They SHALL NOT be exported in `webcompy.__all__` or `webcompy.app.__all__`. Developers define them in `webcompy_server_config.py`, which the CLI reads from the app package or the project root. The `static_files_dir` field in both classes SHALL be a plain `str` value resolved relative to `app_package_path` at the call site.

#### Scenario: ServerConfig defaults
- **WHEN** no `webcompy_server_config.py` exists (in the app package or at the project root) or it does not define `server_config`
- **THEN** `ServerConfig()` defaults SHALL be used (`port=8080`, `dev=False`, `static_files_dir="static"`)

#### Scenario: GenerateConfig defaults
- **WHEN** no `webcompy_server_config.py` exists (in the app package or at the project root) or it does not define `generate_config`
- **THEN** `GenerateConfig()` defaults SHALL be used (`dist="dist"`, `cname=""`, `static_files_dir="static"`)

#### Scenario: runtime_serving is not on ServerConfig or GenerateConfig
- **WHEN** a developer creates `ServerConfig()` or `GenerateConfig()`
- **THEN** neither dataclass SHALL have a `runtime_serving` field
- **AND** `runtime_serving` SHALL only be available on `AppConfig`
