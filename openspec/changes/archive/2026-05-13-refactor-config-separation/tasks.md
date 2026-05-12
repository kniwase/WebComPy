## 1. Create webcompy.cli.config package

- [x] 1.1 Create `webcompy/cli/config/__init__.py` with exports: `WebComPyBuildConfig`, `WebComPyServerConfig`, `LockfileSyncConfig`
- [x] 1.2 Create `webcompy/cli/config/_server_config.py` with `WebComPyServerConfig(port=8080, dev=False)` dataclass
- [x] 1.3 Create `webcompy/cli/config/_build_config.py` with `WebComPyBuildConfig` dataclass accepting `app_module` (ModuleType, required positional) + `app_var` (str, default `"app"`) + all fields from former AppConfig server-only fields + GenerateConfig fields + ServerConfig as nested `server` field; `__post_init__` computes `app_package_path = Path(app_module.__file__).parent` and `app = getattr(app_module, app_var)`
- [x] 1.4 Move `LockfileSyncConfig` from `webcompy/app/_config.py` to `webcompy/cli/config/_server_config.py`

## 2. Refactor WebComPyAppConfig

- [x] 2.1 Replace `AppConfig` in `webcompy/app/_config.py` with `WebComPyAppConfig` containing only: `base_url`, `selector`, `profile`, `hydrate`, `scripts`, `plugins`
- [x] 2.2 Add `selector: str = "#webcompy-app"` field to `WebComPyAppConfig`
- [x] 2.3 Keep `PluginScript` in `webcompy/app/_config.py` (used by browser)
- [x] 2.4 Update `webcompy/app/__init__.py` exports: `WebComPyAppConfig`, `PluginScript`, `WebComPyApp`, `WebComPyPlugin`, `WebComPyPluginException`; remove `LockfileSyncConfig`, `AppConfig` aliases

## 3. Update WebComPyApp

- [x] 3.1 Remove `profile` and `hydrate` parameters from `WebComPyApp.__init__`; use `self.config.profile` and `self.config.hydrate` directly
- [x] 3.2 Remove `selector` parameter from `WebComPyApp.run()`; use `self.config.selector` instead
- [x] 3.3 Update `AppDocumentRoot` to use `selector` from app config for the div ID

## 4. Update CLI modules

- [x] 4.1 Update `_utils.py`: replace `discover_app()` with `discover_config()` that finds `webcompy_config.py` and returns `WebComPyBuildConfig`; add `get_server_config()` / `get_generate_config()` replacements that read from `WebComPyBuildConfig`
- [x] 4.2 Update `_argparser.py`: replace `--app` flag with `--config` flag; keep `--dev`, `--port`, `--dist`, `--serve-all-deps`, `--no-serve-all-deps`, `--wasm-serving`, `--runtime-serving`, `--standalone`, `--no-standalone`, `--wheel-mode`
- [x] 4.3 Update `_server.py`: read all build settings from `WebComPyBuildConfig` instead of `AppConfig`; read server settings from `config.server`; use `config.app` for `WebComPyApp` instance; use `config.app_package_path` for package resolution
- [x] 4.4 Update `_generate.py`: read all build settings from `WebComPyBuildConfig`; read SSG settings (`dist`, `cname`, `static_files_dir`) from `config` directly; use `config.app` and `config.app_package_path`
- [x] 4.5 Update `_html.py`: change bootstrap import from `{name}.bootstrap` to `{name}.app`; use `app.config.selector` for div ID; read build settings from `WebComPyBuildConfig` passed as parameter
- [x] 4.6 Update `_lock.py`: read `config.app_package_path` from `WebComPyBuildConfig`; use `config.app` for dependency resolution
- [x] 4.7 Update `_lockfile_sync.py`: read config from `WebComPyBuildConfig`; use `config.app_package_path`, `config.dependencies`, `config.dependencies_from`, `config.lockfile_sync_config`
- [x] 4.8 Update `resolve_standalone_config()` in `_utils.py` to work on `WebComPyBuildConfig` instead of `AppConfig`

## 5. Update HTML generation and root component

- [x] 5.1 Update `generate_html()` to accept `app_package_name` param; use `app.config.selector` for mount div ID
- [x] 5.2 Update `_root_component.py`: use `app.config.selector` for `_selector` default value and mount div ID
- [x] 5.3 Update SSR div generation: use selector from `WebComPyAppConfig` (strip `#` prefix for HTML `id` attribute)

## 6. Update project templates and scaffolding

- [x] 6.1 Update `webcompy/cli/template_data/webcompy_config.py` to use `WebComPyBuildConfig` and `WebComPyServerConfig` from `webcompy.cli.config`
- [x] 6.2 Rename `webcompy/cli/template_data/app/bootstrap.py` to `app.py`; update import from `webcompy_config` to use new config module
- [x] 6.3 Delete `webcompy/cli/template_data/webcompy_server_config.py` (merged into `webcompy_config.py`)
- [x] 6.4 Update `_init_project.py` to generate `app.py` instead of `bootstrap.py`; generate single `webcompy_config.py` instead of two config files

## 7. Update docs_app

- [x] 7.1 Rename `docs_app/bootstrap.py` to `docs_app/app.py`; update internal imports
- [x] 7.2 Merge `docs_app/webcompy_server_config.py` into `docs_app/webcompy_config.py` using `WebComPyBuildConfig`
- [x] 7.3 Update `docs_app/webcompy_config.py` to use new config structure
- [x] 7.4 Update any references to `bootstrap` → `app` throughout `docs_app/`

## 8. Update tests

- [x] 8.1 Update `tests/test_config_dataclasses.py` to use `WebComPyAppConfig` and `WebComPyBuildConfig`
- [x] 8.2 Update `tests/test_app_instance.py` to use new config classes and remove `profile`/`hydrate`/`selector` params from `WebComPyApp`
- [x] 8.3 Update `tests/test_standalone_config.py` to use `WebComPyBuildConfig`
- [x] 8.4 Update `tests/test_lockfile_sync.py` to use `WebComPyBuildConfig`
- [x] 8.5 Add test for `WebComPyBuildConfig` — app_package_path derivation from `app_module.__file__` and app instance from `getattr(app_module, app_var)`
- [x] 8.6 Add test for `WebComPyAppConfig.selector` and `WebComPyApp.run()` without selector param
- [x] 8.7 Add test for `--config` CLI flag
- [x] 8.8 Add test for library usage (import from `webcompy.app` only, no `webcompy.cli.config` imported)

## 9. Update OpenSpec specs

- [x] 9.1 Update `openspec/specs/app-config/spec.md` to reflect `WebComPyAppConfig` and `WebComPyBuildConfig`
- [x] 9.2 Update `openspec/specs/project-config/spec.md` to reflect single config file and `--config` flag
- [x] 9.3 Update `openspec/specs/cli/spec.md` to reflect new config structure and `app.py` entry point
- [ ] 9.4 Archive this change with `/opsx-archive`