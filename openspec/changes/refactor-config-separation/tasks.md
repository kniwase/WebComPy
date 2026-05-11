## 1. Create webcompy.cli.config package

- [ ] 1.1 Create `webcompy/cli/config/__init__.py` with exports: `WebComPyBuildConfig`, `WebComPyServerConfig`, `LockfileSyncConfig`
- [ ] 1.2 Create `webcompy/cli/config/_server_config.py` with `WebComPyServerConfig(port=8080, dev=False)` dataclass
- [ ] 1.3 Create `webcompy/cli/config/_build_config.py` with `WebComPyBuildConfig` dataclass accepting `app_module` (ModuleType, required positional) + `app_var` (str, default `"app"`) + all fields from former AppConfig server-only fields + GenerateConfig fields + ServerConfig as nested `server` field; `__post_init__` computes `app_package_path = Path(app_module.__file__).parent` and `app = getattr(app_module, app_var)`
- [ ] 1.4 Move `LockfileSyncConfig` from `webcompy/app/_config.py` to `webcompy/cli/config/_server_config.py`

## 2. Refactor WebComPyAppConfig

- [ ] 2.1 Replace `AppConfig` in `webcompy/app/_config.py` with `WebComPyAppConfig` containing only: `base_url`, `selector`, `profile`, `hydrate`, `scripts`, `plugins`
- [ ] 2.2 Add `selector: str = "#webcompy-app"` field to `WebComPyAppConfig`
- [ ] 2.3 Keep `PluginScript` in `webcompy/app/_config.py` (used by browser)
- [ ] 2.4 Update `webcompy/app/__init__.py` exports: `WebComPyAppConfig`, `PluginScript`, `WebComPyApp`, `WebComPyPlugin`, `WebComPyPluginException`; remove `LockfileSyncConfig`, `AppConfig` aliases

## 3. Update WebComPyApp

- [ ] 3.1 Remove `profile` and `hydrate` parameters from `WebComPyApp.__init__`; use `self.config.profile` and `self.config.hydrate` directly
- [ ] 3.2 Remove `selector` parameter from `WebComPyApp.run()`; use `self.config.selector` instead
- [ ] 3.3 Update `AppDocumentRoot` to use `selector` from app config for the div ID

## 4. Update CLI modules

- [ ] 4.1 Update `_utils.py`: replace `discover_app()` with `discover_config()` that finds `webcompy_config.py` and returns `WebComPyBuildConfig`; add `get_server_config()` / `get_generate_config()` replacements that read from `WebComPyBuildConfig`
- [ ] 4.2 Update `_argparser.py`: replace `--app` flag with `--config` flag; keep `--dev`, `--port`, `--dist`, `--serve-all-deps`, `--no-serve-all-deps`, `--wasm-serving`, `--runtime-serving`, `--standalone`, `--no-standalone`, `--wheel-mode`
- [ ] 4.3 Update `_server.py`: read all build settings from `WebComPyBuildConfig` instead of `AppConfig`; read server settings from `config.server`; use `config.app` for `WebComPyApp` instance; use `config.app_package_path` for package resolution
- [ ] 4.4 Update `_generate.py`: read all build settings from `WebComPyBuildConfig`; read SSG settings (`dist`, `cname`, `static_files_dir`) from `config` directly; use `config.app` and `config.app_package_path`
- [ ] 4.5 Update `_html.py`: change bootstrap import from `{name}.bootstrap` to `{name}.app`; use `app.config.selector` for div ID; read build settings from `WebComPyBuildConfig` passed as parameter
- [ ] 4.6 Update `_lock.py`: read `config.app_package_path` from `WebComPyBuildConfig`; use `config.app` for dependency resolution
- [ ] 4.7 Update `_lockfile_sync.py`: read config from `WebComPyBuildConfig`; use `config.app_package_path`, `config.dependencies`, `config.dependencies_from`, `config.lockfile_sync_config`
- [ ] 4.8 Update `resolve_standalone_config()` in `_utils.py` to work on `WebComPyBuildConfig` instead of `AppConfig`

## 5. Update HTML generation and root component

- [ ] 5.1 Update `generate_html()` to accept `WebComPyBuildConfig` for build settings; use `config.app.config.selector` for mount div ID
- [ ] 5.2 Update `_root_component.py`: use `app.config.selector` for `_selector` default value and `_init_node()`
- [ ] 5.3 Update SSR div generation: use selector from `WebComPyAppConfig` (strip `#` prefix for HTML `id` attribute)

## 6. Update project templates and scaffolding

- [ ] 6.1 Update `webcompy/cli/template_data/webcompy_config.py` to use `WebComPyBuildConfig` and `WebComPyServerConfig` from `webcompy.cli.config`
- [ ] 6.2 Rename `webcompy/cli/template_data/app/bootstrap.py` to `app.py`; update import from `webcompy_config` to use new config module
- [ ] 6.3 Delete `webcompy/cli/template_data/webcompy_server_config.py` (merged into `webcompy_config.py`)
- [ ] 6.4 Update `_init_project.py` to generate `app.py` instead of `bootstrap.py`; generate single `webcompy_config.py` instead of two config files

## 7. Update docs_app

- [ ] 7.1 Rename `docs_app/bootstrap.py` to `docs_app/app.py`; update internal imports
- [ ] 7.2 Merge `docs_app/webcompy_server_config.py` into `docs_app/webcompy_config.py` using `WebComPyBuildConfig`
- [ ] 7.3 Update `docs_app/webcompy_config.py` to use new config structure
- [ ] 7.4 Update any references to `bootstrap` → `app` throughout `docs_app/`

## 8. Update tests

- [ ] 8.1 Update `tests/test_config_dataclasses.py` to use `WebComPyAppConfig` and `WebComPyBuildConfig`
- [ ] 8.2 Update `tests/test_app_instance.py` to use new config classes and remove `profile`/`hydrate`/`selector` params from `WebComPyApp`
- [ ] 8.3 Update `tests/test_standalone_config.py` to use `WebComPyBuildConfig`
- [ ] 8.4 Update `tests/test_lockfile_sync.py` to use `WebComPyBuildConfig`
- [ ] 8.5 Add test for `WebComPyBuildConfig` — app_package_path derivation from `app_module.__file__` and app instance from `getattr(app_module, app_var)`
- [ ] 8.6 Add test for `WebComPyAppConfig.selector` and `WebComPyApp.run()` without selector param
- [ ] 8.7 Add test for `--config` CLI flag
- [ ] 8.8 Add test for library usage (import from `webcompy.app` only, no `webcompy.cli.config` imported)

## 9. Update OpenSpec specs

- [ ] 9.1 Update `openspec/specs/app-config/spec.md` to reflect `WebComPyAppConfig` and `WebComPyBuildConfig`
- [ ] 9.2 Update `openspec/specs/project-config/spec.md` to reflect single config file and `--config` flag
- [ ] 9.3 Update `openspec/specs/cli/spec.md` to reflect new config structure and `app.py` entry point
- [ ] 9.4 Archive this change with `/opsx-archive`