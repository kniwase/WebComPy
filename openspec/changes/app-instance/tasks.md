## 1. Configuration Dataclasses

- [ ] 1.1 Create `webcompy/app/_config.py` with `AppConfig` dataclass (base_url, dependencies, assets) and `__post_init__` validation for base_url normalization
- [ ] 1.2 Add `ServerConfig` dataclass (port, dev, static_files_dir) to `_config.py`
- [ ] 1.3 Add `GenerateConfig` dataclass (dist, cname, static_files_dir) to `_config.py`
- [ ] 1.4 Add unit tests for all three config dataclasses (normalization, defaults, validation)
- [ ] 1.5 Export config classes from `webcompy/app/__init__.py` and `webcompy/__init__.py`

## 2. WebComPyApp Public API — Transparent Properties

- [ ] 2.1 Add `config: AppConfig` parameter to `WebComPyApp.__init__` with default `AppConfig()`
- [ ] 2.2 Add transparent property forwarding to `WebComPyApp`: `routes`, `router_mode`, `set_path()`, `head`, `style`, `scripts`, `set_title()`, `set_meta()`, `append_link()`, `append_script()`, `set_head()`, `update_head()`
- [ ] 2.3 Add `DeprecationWarning` to `WebComPyApp.__component__` property
- [ ] 2.4 Update `WebComPyApp.__init__` to pass `AppConfig.base_url` to `AppDocumentRoot` so the router can use it
- [ ] 2.5 Add unit tests for all forwarded properties and the deprecation warning

## 3. Browser Entry Point — app.run()

- [ ] 3.1 Add `app.run(selector: str = "#webcompy-app")` method to `WebComPyApp` with environment guard (raise if not Emscripten)
- [ ] 3.2 Modify `AppDocumentRoot._init_node()` to accept a selector parameter and use `querySelector` instead of hardcoded `getElementById`
- [ ] 3.3 Add mount-point-not-found error handling in `app.run()`
- [ ] 3.4 Update `AppDocumentRoot._render()` to handle loading screen removal relative to custom mount selector
- [ ] 3.5 Update `_html.py` generated PyScript bootstrap code from `app.__component__.render()` to `app.run()`
- [ ] 3.6 Add unit tests for `app.run()` (environment guard, selector handling, deprecation of old pattern)

## 4. Server Entry Points — app.serve() and app.asgi_app

- [ ] 4.1 Add `app.asgi_app` cached property that calls `create_asgi_app(self, ...)` using `AppConfig` instead of `WebComPyConfig`
- [ ] 4.2 Refactor `create_asgi_app()` to accept `WebComPyApp` and `AppConfig` directly instead of `WebComPyConfig`
- [ ] 4.3 Add `app.serve(config: ServerConfig | None = None, **kwargs)` method that calls `uvicorn.run(self.asgi_app, ...)` with environment guard
- [ ] 4.4 Ensure `app.asgi_app` can be mounted into other Starlette/FastAPI apps via `Mount`
- [ ] 4.5 Add integration tests for `app.serve()` and `app.asgi_app`

## 5. SSG Entry Point — app.generate()

- [ ] 5.1 Add `app.generate(config: GenerateConfig | None = None, **kwargs)` method with environment guard
- [ ] 5.2 Refactor `_generate.py` logic into `app.generate()` or make `generate_static_site()` delegate to `app.generate()`
- [ ] 5.3 Ensure `app.generate()` uses `AppConfig` from the app instance for base_url, dependencies, and assets
- [ ] 5.4 Add integration tests for `app.generate()`

## 6. Singleton Removal — RouterView

- [ ] 6.1 Remove `RouterView._instance` ClassVar and singleton enforcement from `RouterView.__init__`
- [ ] 6.2 Add unit tests for multiple RouterView instances coexisting
- [ ] 6.3 Remove TODO comment about App Instance migration in `RouterView`

## 7. Per-App State — ComponentStore and _defer_*

- [ ] 7.1 Remove `_default_component_store` module global from `webcompy/components/_generator.py`
- [ ] 7.2 Update `ComponentGenerator.__init__` to use `inject(_COMPONENT_STORE_KEY, default=None)` — if scope exists, register immediately; if not, defer registration
- [ ] 7.3 Create per-app `ComponentStore` in `WebComPyApp.__init__` and provide into `app._di_scope`
- [ ] 7.4 Update `AppDocumentRoot.__init__` to provide the app-specific `ComponentStore` instead of `_default_component_store`
- [ ] 7.5 Update `AppDocumentRoot.style` to use `inject(_COMPONENT_STORE_KEY)` without default fallback
- [ ] 7.6 Move `_defer_after_rendering_depth` and `_deferred_after_rendering_callbacks` to `WebComPyApp` as instance attributes
- [ ] 7.7 Add `_active_app_context: ContextVar[WebComPyApp | None]` and update `start_defer_after_rendering()` and `end_defer_after_rendering()` to use it
- [ ] 7.8 Update `SwitchElement._refresh()` and other callers to use `_active_app_context`
- [ ] 7.9 Update `AppDocumentRoot._render()` to set `_active_app_context` before rendering and reset after
- [ ] 7.10 Add unit tests for per-app ComponentStore isolation and _defer_* per-app state

## 8. Remove _root_di_scope Global

- [ ] 8.1 Remove `_root_di_scope`, `_set_root_di_scope`, `_get_root_di_scope` from `webcompy/di/_scope.py`
- [ ] 8.2 Remove `_root_di_scope` fallback from `provide()` and `inject()` in `webcompy/di/__init__.py`
- [ ] 8.3 Remove `_set_root_di_scope(di_scope)` call from `AppDocumentRoot.__init__`
- [ ] 8.4 Remove `_active_di_scope.set(app._di_scope)` from `_server.py` and `_generate.py` (lifecycle methods will manage scope internally)
- [ ] 8.5 Verify E2E tests pass without `_root_di_scope` fallback (especially browser context tests)
- [ ] 8.6 Update `tests/conftest.py` — remove `reset_di_scope` fixture if no longer needed

## 9. CLI Backward Compatibility

- [ ] 9.1 Add `DeprecationWarning` to `WebComPyConfig.__init__`
- [ ] 9.2 Update CLI argparser to accept `--app` option specifying import path (e.g., `my_app.app:app`)
- [ ] 9.3 Update `get_app()` in `_utils.py` to support both legacy `bootstrap.py` and new `app.run()`-compatible patterns
- [ ] 9.4 Update `_asgi_app.py` to support both `WebComPyConfig` and direct `WebComPyApp.asgi_app` patterns (with deprecation warning for old path)
- [ ] 9.5 Add deprecation warning tests

## 10. Template and Documentation Updates

- [ ] 10.1 Update `webcompy/cli/template_data/app/bootstrap.py` to use `AppConfig` and `app.run()` pattern
- [ ] 10.2 Update `webcompy/cli/template_data/webcompy_config.py` template to use `AppConfig` (with deprecation notice)
- [ ] 10.3 Update `AGENTS.md` with new app instance API
- [ ] 10.4 Update existing E2E test bootstrap files to use new pattern if applicable

## 11. Final Verification

- [ ] 11.1 Run full test suite (`uv run python -m pytest tests/ --tb=short`)
- [ ] 11.2 Run lint (`uv run ruff check .`) and format (`uv run ruff format .`)
- [ ] 11.3 Run type check (`uv run pyright`)
- [ ] 11.4 Verify E2E tests pass with new app.run() bootstrap pattern