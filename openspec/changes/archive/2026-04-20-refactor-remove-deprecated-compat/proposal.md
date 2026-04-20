## Why

WebComPy is pre-release software where breaking changes are acceptable. After the App Instance system (PR #105) introduced `AppConfig`, `ServerConfig`, `GenerateConfig`, forwarded properties, and `--app` CLI support, several deprecated compatibility layers remain: `WebComPyConfig` (legacy config class with `DeprecationWarning`), `app.__component__` (deprecated property), `webcompy_config.py` file-based discovery pattern, and internal `AppConfig`-to-`WebComPyConfig` conversion bridges. These add maintenance burden, confuse the API surface, and obscure the clean architecture underneath. Removing them now — while breaking changes are still acceptable — simplifies the codebase and eliminates two separate configuration paths.

## What Changes

- **BREAKING**: Remove `WebComPyConfig` class entirely (`webcompy/cli/_config.py`)
- **BREAKING**: Remove `app.__component__` deprecated property from `WebComPyApp`
- **BREAKING**: Remove legacy config discovery (`get_config()`, `get_app(config)`, `build_config_from_app()`)
- **BREAKING**: Remove `_asgi_app.py` (legacy ASGI entry point that relied on `webcompy_config.py`)
- **BREAKING**: Replace the `webcompy_config.py` pattern with a new two-file configuration system:
  - `webcompy_config.py` — contains `app_import_path`, `app_config` (shared between browser and server)
  - `webcompy_server_config.py` — contains `server_config` and `generate_config` (server-only)
- **BREAKING**: Change CLI function signatures to accept `AppConfig`/`ServerConfig`/`GenerateConfig` instead of `WebComPyConfig`
- **BREAKING**: Remove `WebComPyConfig` from public exports (`webcompy.cli.__init__`)
- **BREAKING**: Remove `ServerConfig` and `GenerateConfig` from public API exports (they become internal)
- Refactor `generate_html()`, `create_asgi_app()`, `run_server()`, `generate_static_site()` to use `app.config` and typed config dataclasses instead of `WebComPyConfig`
- Update `webcompy init` template to use the new configuration pattern
- Update E2E test fixtures to use the new configuration pattern
- CLI flags (`--dev`, `--port`, `--dist`) remain and override values from config files

## Capabilities

### New Capabilities

- `project-config`: Two-file project configuration pattern (`webcompy_config.py` for app-shared settings including `app_import_path`, `webcompy_server_config.py` for server/SSG-only settings). CLI discovers app instance via `app_import_path` when `--app` is not specified.

### Modified Capabilities

- `app`: Remove `app.__component__` deprecated property. Requirements change from "SHALL emit DeprecationWarning" to property does not exist.
- `app-config`: Remove `WebComPyConfig`. `AppConfig` is now the sole configuration class. `ServerConfig` and `GenerateConfig` become internal-only.
- `app-lifecycle`: Remove all `WebComPyConfig` mentions and internal conversion. Change `create_asgi_app` and `generate_static_site` signatures. Remove `_asgi_app.py` reference. `AppConfig` is never "converted" to another config type.
- `cli`: Remove `WebComPyConfig` discovery pattern. Replace with `webcompy_config.py` / `webcompy_server_config.py` pattern. Remove `WebComPyConfig` deprecation requirements. Remove `_asgi_app.py` module.
- `architecture`: Remove dual discovery pattern (legacy `webcompy_config.py` + new `WebComPyApp`). Project structure uses the new two-file config pattern.

## Impact

- **API**: `WebComPyConfig`, `app.__component__`, `get_config()`, `get_app(config)`, `build_config_from_app()` removed from public API
- **API**: `ServerConfig`, `GenerateConfig` removed from `webcompy` and `webcompy.app` top-level exports (internal only)
- **CLI**: `create_asgi_app(app, server_config=None)`, `generate_static_site(app, generate_config=None)`, `run_server(app=None)` changed signatures
- **CLI**: `generate_html()` signature changes from `(config: WebComPyConfig, ...)` to `(app: WebComPyApp, ...)`
- **Project template**: `webcompy init` generates new config files (`webcompy_config.py` with `app_import_path` + `app_config`, `webcompy_server_config.py`)
- **Tests**: `test_config.py` (WebComPyConfig tests) removed. deprecation tests in `test_app_instance.py` removed. E2E fixtures updated.
- **Files deleted**: `webcompy/cli/_config.py`, `webcompy/cli/_asgi_app.py`

## Known Issues Addressed

None directly, but this removes the module-level fallback/legacy complexity that was documented as a known limitation in the app-instance change.

## Non-goals

- Adding new features or capabilities beyond config cleanup
- Changing the browser runtime behavior
- Modifying the DI system
- Changing the component, element, or reactive APIs