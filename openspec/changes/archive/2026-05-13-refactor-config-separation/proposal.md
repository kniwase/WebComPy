## Why

WebComPy's `AppConfig` mixes browser-relevant settings with server-only build settings in a single dataclass. This prevents using WebComPy as a library (importing components and mounting them in a PyScript page without the full build pipeline), because the browser must import `AppConfig` which carries irrelevant fields like `app_package`, `dependencies`, `serve_all_deps`, etc. Separating these concerns cleanly enables a Vue.js-like dual usage model: library mode (CDN import, spot mounting) and framework mode (CLI-driven SSR/SSG builds).

Additionally, the mount selector (`app.run("#webcompy-app")`) is not part of the config, causing inconsistency between SSR/SSG-generated HTML and browser-side mounting. Making the selector a config field ensures the same value is used across all environments.

## What Changes

- **BREAKING**: Replace `AppConfig` with `WebComPyAppConfig` (lightweight, browser-safe: `base_url`, `selector`, `profile`, `hydrate`, `scripts`, `plugins`)
- **BREAKING**: Create `WebComPyBuildConfig` (server-only: `app_module`, `app_var`, `app`, `app_package_path`, `dependencies`, `serve_all_deps`, `wasm_serving`, `runtime_serving`, `standalone`, `wheel_mode`, `assets`, `version`, `dist`, `cname`, `static_files_dir`, `lockfile_sync_config`, `server`). Takes `app_module` (the app's Python module object) as first required positional arg + `app_var: str = "app"` for the instance variable name. `app_package_path` is derived from `app_module.__file__`.
- **BREAKING**: Create `WebComPyServerConfig` (ASGI server settings: `port`, `dev`) as a member of `WebComPyBuildConfig`
- **BREAKING**: Remove `GenerateConfig` — its fields are absorbed into `WebComPyBuildConfig` (`dist`, `cname`, `static_files_dir`)
- **BREAKING**: Rename `bootstrap.py` → `app.py` in project templates and generated HTML
- **BREAKING**: Move `WebComPyBuildConfig` and `WebComPyServerConfig` to `webcompy.cli.config` package (not `webcompy.app`) to keep browser imports clean and ensure they are excluded from browser wheels alongside `webcompy/cli/`
- **BREAKING**: Replace `--app` CLI flag with `--config` flag for specifying `webcompy_config.py` path
- **BREAKING**: Consolidate `webcompy_config.py` and `webcompy_server_config.py` into a single `webcompy_config.py` containing `config = WebComPyBuildConfig(app, ...)`
- **BREAKING**: Remove `app_import_path` from `webcompy_config.py` — `WebComPyBuildConfig.app` replaces it
- **BREAKING**: Remove `profile` and `hydrate` parameters from `WebComPyApp.__init__` — use `WebComPyAppConfig` only
- **BREAKING**: Remove `selector` parameter from `WebComPyApp.run()` — use `WebComPyAppConfig.selector` instead
- Add `selector` field to `WebComPyAppConfig` (default `"#webcompy-app"`)

## Capabilities

### New Capabilities
- `config-separation`: Clean separation of browser-relevant config (`WebComPyAppConfig` in `webcompy.app`) from server-only build config (`WebComPyBuildConfig` / `WebComPyServerConfig` in `webcompy.cli.config`)

### Modified Capabilities
- `app-config`: Rename `AppConfig` to `WebComPyAppConfig`, remove server-only fields, add `selector`
- `project-config`: Consolidate two-file config into single `webcompy_config.py` with `WebComPyBuildConfig`, remove `app_import_path`, replace `--app` with `--config`
- `cli`: Update all CLI commands to use `WebComPyBuildConfig` instead of `AppConfig`/`ServerConfig`/`GenerateConfig`, rename `bootstrap.py` references to `app.py`

## Impact

- **`webcompy/app/_config.py`**: Slimmed to `WebComPyAppConfig` and `PluginScript` only
- **`webcompy/cli/config/`**: New package with `_build_config.py`, `_server_config.py`, `__init__.py` (excluded from browser wheels via existing `cli/` exclusion)
- **`webcompy/app/_app.py`**: `WebComPyApp.__init__` loses `profile`/`hydrate` params; `run()` loses `selector` param
- **`webcompy/cli/`**: All CLI modules updated to read from `WebComPyBuildConfig` instead of `app.config.*`
- **`webcompy/cli/_html.py`**: Bootstrap import changes from `{name}.bootstrap` to `{name}.app`
- **`webcompy/cli/template_data/`**: Template files updated for new structure
- **`docs_app/`**: Migrate to new config structure
- **Tests**: All config-related tests updated
- **OpenSpec specs**: `app-config`, `project-config`, `cli` specs updated

## Known Issues Addressed

- Module-level fallbacks (`_app_di_scope`, `_app_instance`) hold only one app reference in browser environment, limiting true multi-app isolation — while not directly resolved, the config separation removes server-only state from browser imports, reducing unnecessary coupling