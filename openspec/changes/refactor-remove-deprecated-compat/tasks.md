## 1. Remove `WebComPyConfig` and internal conversion layer

- [ ] 1.1 Delete `webcompy/cli/_config.py` (entire `WebComPyConfig` class)
- [ ] 1.2 Remove `build_config_from_app()` from `webcompy/cli/_utils.py`
- [ ] 1.3 Remove `get_config()` from `webcompy/cli/_utils.py`
- [ ] 1.4 Remove `get_app(config)` from `webcompy/cli/_utils.py`
- [ ] 1.5 Remove `import warnings` and all `warnings.catch_warnings()`/`DeprecationWarning` suppression from `webcompy/cli/_utils.py`
- [ ] 1.6 Remove `WebComPyConfig` import and export from `webcompy/cli/__init__.py`

## 2. Remove `app.__component__` deprecated property

- [ ] 2.1 Remove `__component__` property and `import warnings` from `webcompy/app/_app.py`

## 3. Remove `ServerConfig` and `GenerateConfig` from public exports

- [ ] 3.1 Remove `ServerConfig` and `GenerateConfig` from `webcompy/__init__.py` `__all__` and imports
- [ ] 3.2 Remove `ServerConfig` and `GenerateConfig` from `webcompy/app/__init__.py` `__all__` and imports
- [ ] 3.3 Add `ServerConfig` and `GenerateConfig` imports in CLI-internal files where needed

## 4. Refactor `generate_html()` to accept `WebComPyApp` instead of `WebComPyConfig`

- [ ] 4.1 Change `generate_html()` signature from `(config: WebComPyConfig, dev_mode, prerender, app_version, app_package_name)` to `(app: WebComPyApp, dev_mode, prerender, app_version, app_package_name)`
- [ ] 4.2 Replace all `config.base` → `app.config.base_url`, `config.dependencies` → `app.config.dependencies`, `config.app_package_path.name` → `app.config.app_package_path.name` inside `generate_html()`
- [ ] 4.3 Remove `from webcompy.cli._config import WebComPyConfig` from `_html.py`

## 5. Refactor `create_asgi_app()` and `run_server()`

- [ ] 5.1 Change `create_asgi_app(app, config: WebComPyConfig | None, dev_mode)` to `create_asgi_app(app, server_config: ServerConfig | None)`
- [ ] 5.2 Replace all `config.` field accesses with `app.config.` / `server_config.` inside `create_asgi_app()`
- [ ] 5.3 Move `dev_mode` logic into `ServerConfig.dev` (SSE route inclusion based on `server_config.dev`)
- [ ] 5.4 Refactor `run_server()` to use new config discovery (`webcompy_config.py` / `--app` / `webcompy_server_config.py`)
- [ ] 5.5 Remove `from webcompy.cli._config import WebComPyConfig` and `build_config_from_app`/`get_config`/`get_app` imports from `_server.py`

## 6. Refactor `generate_static_site()`

- [ ] 6.1 Change `generate_static_site(app)` to `generate_static_site(app, generate_config: GenerateConfig | None)`
- [ ] 6.2 Replace all `config.` field accesses with `app.config.` / `generate_config.` inside `generate_static_site()`
- [ ] 6.3 Refactor config discovery to use `webcompy_config.py` / `--app` / `webcompy_server_config.py`
- [ ] 6.4 Remove `build_config_from_app`/`get_config`/`get_app` imports from `_generate.py`

## 7. Implement new config discovery functions

- [ ] 7.1 Add `get_server_config()` function to `_utils.py` that reads `webcompy_server_config.py` (or returns defaults)
- [ ] 7.2 Add `get_generate_config()` function to `_utils.py` that reads `webcompy_server_config.py` (or returns defaults)
- [ ] 7.3 Add `discover_app()` function to `_utils.py` that resolves app via `--app` flag or `webcompy_config.py.app_import_path`
- [ ] 7.4 Remove `_asgi_app.py` (legacy ASGI entry point)

## 8. Update `run_server()` and `generate_static_site()` with CLI flag overrides

- [ ] 8.1 Wire `--dev` flag to override `ServerConfig.dev` in `run_server()`
- [ ] 8.2 Wire `--port` flag to override `ServerConfig.port` in `run_server()`
- [ ] 8.3 Wire `--dist` flag to override `GenerateConfig.dist` in `generate_static_site()`

## 9. Update project template (`webcompy init`)

- [ ] 9.1 Replace `webcompy/cli/template_data/webcompy_config.py` with new format (`app_import_path` + `app_config`)
- [ ] 9.2 Create `webcompy/cli/template_data/webcompy_server_config.py` with `server_config` and `generate_config`
- [ ] 9.3 Update `webcompy/cli/template_data/app/bootstrap.py` to import `app_config` from `webcompy_config`

## 10. Update E2E test fixtures

- [ ] 10.1 Rewrite `tests/e2e/webcompy_config.py` to use `app_import_path` + `app_config`
- [ ] 10.2 Create `tests/e2e/webcompy_server_config.py` with `server_config` and `generate_config`

## 11. Update unit tests

- [ ] 11.1 Delete `tests/test_config.py` (WebComPyConfig tests) — replace with AppConfig-focused tests where needed
- [ ] 11.2 Remove `TestWebComPyAppComponentDeprecation` and `TestDeprecationWarnings` from `tests/test_app_instance.py`
- [ ] 11.3 Remove `app.__component__` references from `tests/test_app_instance.py` forwarding tests
- [ ] 11.4 Update `tests/test_config_dataclasses.py` if `ServerConfig`/`GenerateConfig` export paths change
- [ ] 11.5 Add tests for new config discovery functions (`discover_app()`, `get_server_config()`, `get_generate_config()`)

## 12. Update spec documents

- [ ] 12.1 Update `openspec/specs/app/spec.md` — remove `__component__` requirement
- [ ] 12.2 Update `openspec/specs/app-config/spec.md` — remove `WebComPyConfig`, mark `ServerConfig`/`GenerateConfig` as internal
- [ ] 12.3 Update `openspec/specs/app-lifecycle/spec.md` — remove `WebComPyConfig` mentions, update signatures
- [ ] 12.4 Update `openspec/specs/cli/spec.md` — remove `WebComPyConfig` pattern, add two-file config pattern
- [ ] 12.5 Update `openspec/specs/architecture/spec.md` — remove dual discovery pattern
- [ ] 12.6 Add `openspec/specs/project-config/spec.md` as new spec
- [ ] 12.7 Update `openspec/config.yaml` known issues if applicable

## 13. Lint, typecheck, and test

- [ ] 13.1 Run `uv run ruff check .` and fix issues
- [ ] 13.2 Run `uv run ruff format .`
- [ ] 13.3 Run `uv run pyright`
- [ ] 13.4 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 13.5 Run E2E tests if applicable