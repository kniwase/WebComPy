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

## 6. Singleton Removal — Router and RouterView

- [ ] 6.1 Remove `Router._instance` ClassVar and singleton enforcement from `Router.__init__`
- [ ] 6.2 Remove `RouterView._instance` ClassVar and singleton enforcement from `RouterView.__init__`
- [ ] 6.3 Add `__set_router__()` deprecation warnings on `RouterView` and `TypedRouterLink`
- [ ] 6.4 Pass `Router` reference to `RouterView.__init__` and `TypedRouterLink.__init__` via `_active_app_context` ContextVar or constructor parameter (bridge until DI)
- [ ] 6.5 Remove `reset_router_singleton` and `reset_router_link` fixtures from `tests/conftest.py`
- [ ] 6.6 Remove `Router._instance = None` workarounds from `tests/test_router_advanced.py`
- [ ] 6.7 Add unit tests for multiple Router/RouterView instances coexisting

## 7. Per-App State — HeadPropsStore and ComponentStore

- [ ] 7.1 Move `HeadPropsStore` from `Component._head_props` ClassVar to `WebComPyApp` instance attribute
- [ ] 7.2 Add `_active_app_context` ContextVar to propagate app reference through the component tree
- [ ] 7.3 Update `Component._set_title()` and `Component._set_meta()` to use app-scoped HeadPropsStore via context
- [ ] 7.4 Update `Component._remove_element()` cleanup to use app-scoped HeadPropsStore
- [ ] 7.5 Remove `@_instantiate` decorator from `ComponentStore`; make it a regular class
- [ ] 7.6 Add module-level `_default_component_store` for backward compat during `ComponentGenerator.__init__` auto-registration
- [ ] 7.7 Add `ComponentStore` instance to `WebComPyApp`; update `AppDocumentRoot.style` to use app-specific store
- [ ] 7.8 Move `_defer_after_rendering_depth` and `_deferred_after_rendering_callbacks` to app scope
- [ ] 7.9 Update `start_defer_after_rendering()` and `end_defer_after_rendering()` to use app context
- [ ] 7.10 Add unit tests for per-app HeadPropsStore and ComponentStore isolation

## 8. CLI Backward Compatibility

- [ ] 8.1 Add `DeprecationWarning` to `WebComPyConfig.__init__`
- [ ] 8.2 Update CLI argparser to accept `--app` option specifying import path (e.g., `my_app.app:app`)
- [ ] 8.3 Update `get_app()` in `_utils.py` to support both legacy `bootstrap.py` and new `app.run()`-compatible patterns
- [ ] 8.4 Update `_asgi_app.py` to support both `WebComPyConfig` and direct `WebComPyApp.asgi_app` patterns (with deprecation warning for old path)
- [ ] 8.5 Add deprecation warning tests

## 9. Template and Documentation Updates

- [ ] 9.1 Update `webcompy/cli/template_data/app/bootstrap.py` to use `AppConfig` and `app.run()` pattern
- [ ] 9.2 Update `webcompy/cli/template_data/webcompy_config.py` template to use `AppConfig` (with deprecation notice)
- [ ] 9.3 Update `AGENTS.md` with new app instance API
- [ ] 9.4 Update existing E2E test bootstrap files to use new pattern if applicable

## 10. Final Verification

- [ ] 10.1 Run full test suite (`uv run python -m pytest tests/ --tb=short`)
- [ ] 10.2 Run lint (`uv run ruff check .`) and format (`uv run ruff format .`)
- [ ] 10.3 Run type check (`uv run pyright`)
- [ ] 10.4 Verify E2E tests pass with new app.run() bootstrap pattern