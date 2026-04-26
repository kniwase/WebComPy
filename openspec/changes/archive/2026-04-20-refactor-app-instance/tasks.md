## 1. Configuration Dataclasses

- [x] 1.1 Create `webcompy/app/_config.py` with `AppConfig` dataclass (base_url, dependencies, assets, app_package) and `__post_init__` validation for base_url normalization
- [x] 1.2 Add `ServerConfig` dataclass (port, dev, static_files_dir) to `_config.py`
- [x] 1.3 Add `GenerateConfig` dataclass (dist, cname, static_files_dir) to `_config.py`
- [x] 1.4 Add unit tests for all three config dataclasses (normalization, defaults, validation)
- [x] 1.5 Export config classes from `webcompy/app/__init__.py` and `webcompy/__init__.py`

## 2. WebComPyApp Public API — Transparent Properties

- [x] 2.1 Add `config: AppConfig` parameter to `WebComPyApp.__init__` with default `AppConfig()`
- [x] 2.2 Add transparent property forwarding to `WebComPyApp`: `routes`, `router_mode`, `set_path()`, `head`, `style`, `scripts`, `set_title()`, `set_meta()`, `append_link()`, `append_script()`, `set_head()`, `update_head()`
- [x] 2.3 Add `DeprecationWarning` to `WebComPyApp.__component__` property
- [x] 2.4 Update `WebComPyApp.__init__` to pass `AppConfig.base_url` to `AppDocumentRoot` so the router can use it
- [x] 2.5 Add unit tests for all forwarded properties and the deprecation warning

## 3. Browser Entry Point — app.run()

- [x] 3.1 Add `app.run(selector: str = "#webcompy-app")` method to `WebComPyApp` with environment guard (raise if not Emscripten)
- [x] 3.2 Modify `AppDocumentRoot._init_node()` to accept a selector parameter and use `querySelector` instead of hardcoded `getElementById`
- [x] 3.3 Add mount-point-not-found error handling in `app.run()`
- [x] 3.4 Update `AppDocumentRoot._render()` to handle loading screen removal relative to custom mount selector
- [x] 3.5 Update `_html.py` generated PyScript bootstrap code from `app.__component__.render()` to `app.run()`
- [x] 3.6 Add unit tests for `app.run()` (environment guard, selector handling, deprecation of old pattern)

## 4. Server Entry Points — create_asgi_app and run_server

- [x] 4.1 Refactor `create_asgi_app()` to accept `WebComPyApp` as primary argument (config auto-built from `AppConfig` when not provided)
- [x] 4.2 Update `run_server()` to accept optional `WebComPyApp` argument
- [x] 4.3 Replace `_active_di_scope.set()` calls with `app.di_scope` context manager in `_server.py`
- [x] 4.4 Verify E2E tests pass with updated server entry points

## 5. SSG Entry Point — generate_static_site

- [x] 5.1 Update `generate_static_site()` to accept optional `WebComPyApp` argument
- [x] 5.2 Replace `_active_di_scope.set()` calls with `app.di_scope` context manager in `_generate.py`
- [x] 5.3 Verify E2E tests pass with updated SSG entry points

## 6. Singleton Removal — RouterView

- [x] 6.1 Remove `RouterView._instance` ClassVar and singleton enforcement from `RouterView.__init__`
- [x] 6.2 Add unit tests for multiple RouterView instances coexisting
- [x] 6.3 Remove TODO comment about App Instance migration in `RouterView`

## 7. Per-App State — ComponentStore and _defer_*

- [x] 7.1 Remove `_default_component_store` module global from `webcompy/components/_generator.py`
- [x] 7.2 Update `ComponentGenerator.__init__` to use `inject(_COMPONENT_STORE_KEY, default=None)` — if scope exists, register immediately; if not, defer registration
- [x] 7.3 Create per-app `ComponentStore` in `WebComPyApp.__init__` and provide into `app._di_scope`
- [x] 7.4 Update `AppDocumentRoot.__init__` to provide the app-specific `ComponentStore` instead of `_default_component_store`
- [x] 7.5 Update `AppDocumentRoot.style` to use `inject(_COMPONENT_STORE_KEY)` without default fallback
- [x] 7.6 Move `_defer_after_rendering_depth` and `_deferred_after_rendering_callbacks` to `WebComPyApp` as instance attributes
- [x] 7.7 Add `_active_app_context: ContextVar[WebComPyApp | None]` and update `start_defer_after_rendering()` and `end_defer_after_rendering()` to use it
- [x] 7.8 Update `SwitchElement._refresh()` and other callers to use `_active_app_context`
- [x] 7.9 Update `AppDocumentRoot._render()` to set `_active_app_context` before rendering and reset after
- [x] 7.10 Add unit tests for per-app ComponentStore isolation and _defer_* per-app state

## 8. Remove _root_di_scope Global

- [x] 8.1 Remove `_root_di_scope`, `_set_root_di_scope`, `_get_root_di_scope` from `webcompy/di/_scope.py`
- [x] 8.2 Remove `_root_di_scope` fallback from `provide()` and `inject()` in `webcompy/di/__init__.py`
- [x] 8.3 Remove `_set_root_di_scope(di_scope)` call from `AppDocumentRoot.__init__`
- [x] 8.4 Remove `_active_di_scope.set(app._di_scope)` from `_server.py` and `_generate.py` (lifecycle methods will manage scope internally)
- [x] 8.5 Verify E2E tests pass without `_root_di_scope` fallback (especially browser context tests)
- [x] 8.6 Update `tests/conftest.py` — remove `reset_di_scope` fixture if no longer needed

## 9. CLI Backward Compatibility

- [x] 9.1 Add `DeprecationWarning` to `WebComPyConfig.__init__`
- [x] 9.2 Update CLI argparser to accept `--app` option specifying import path (e.g., `my_app.app:app`)
- [x] 9.3 Update `get_app()` in `_utils.py` to support both legacy `bootstrap.py` and new `app.run()`-compatible patterns
- [x] 9.4 Update `_asgi_app.py` to use updated `create_asgi_app` and `get_app` patterns
- [x] 9.5 Add deprecation warning tests

## 10. Template and Documentation Updates

- [x] 10.1 Update `webcompy/cli/template_data/app/bootstrap.py` to use `AppConfig` and `app.run()` pattern
- [x] 10.2 Update `webcompy/cli/template_data/webcompy_config.py` template to use `AppConfig` (with deprecation notice)
- [x] 10.3 Update `AGENTS.md` with new app instance API
- [x] 10.4 Update existing E2E test bootstrap files to use new pattern if applicable

## 11. Final Verification

- [x] 11.1 Run full test suite (`uv run python -m pytest tests/ --tb=short`)
- [x] 11.2 Run lint (`uv run ruff check .`) and format (`uv run ruff format .`)
- [x] 11.3 Run type check (`uv run pyright`)
- [x] 11.4 Verify E2E tests pass with new app.run() bootstrap pattern