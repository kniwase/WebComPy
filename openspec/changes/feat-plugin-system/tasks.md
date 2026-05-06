## 1. New Module: webcompy/plugin/

- [ ] 1.1 Create `webcompy/plugin/` package directory with `__init__.py`
- [ ] 1.2 Define `WebComPyPlugin` base class in `webcompy/plugin/_plugin.py` with `name`, `version` class variables, static methods `get_providers()` and `get_scripts()`, and lifecycle hooks `on_app_init(self, app)`, `on_app_ready(self, app)`
- [ ] 1.3 Define `PluginManager` class in `webcompy/plugin/_manager.py` with `discover(plugin_paths)`, `init_all()`, `call_on_app_ready(app)`, and `scripts` property
- [ ] 1.4 Define `WebComPyPluginException` exception class
- [ ] 1.5 Export `WebComPyPlugin`, `PluginManager`, `WebComPyPluginException` from `webcompy/plugin/__init__.py`

## 2. AppConfig Changes

- [ ] 2.1 Add `plugins: list[str] = field(default_factory=list)` field to `AppConfig` in `webcompy/app/_config.py`

## 3. WebComPyApp Integration

- [ ] 3.1 In `WebComPyApp.__init__()`, create `PluginManager` instance, call `discover()` and `init_all()` after DI scope setup and before `AppDocumentRoot` creation. Store router as `self._router` and add a `router` property exposing it.
- [ ] 3.2 In `WebComPyApp.run()`, call `on_app_ready(app)` on all plugins before the first render
- [ ] 3.3 Export `PluginManager`, `WebComPyPlugin` from `webcompy/app/__init__.py` (re-export from `webcompy.plugin`). Re-export `WebComPyPluginException` as well.

## 4. Router Hooks

- [ ] 4.1 Add `before_route_change: list[Callable]`, `after_route_change: list[Callable]`, `on_route_error: list[Callable]` to `Router` class in `webcompy/router/_router.py`
- [ ] 4.2 In `webcompy/router/_change_event_handler.py`, dispatch `before_route_change` callbacks in `Location.__set_path__()` before updating the signal value (cancel on `False`)
- [ ] 4.3 Dispatch `after_route_change` callbacks after successful navigation
- [ ] 4.4 Wrap route resolution in try/except and dispatch `on_route_error` callbacks on error

## 5. HTML Generation Integration

- [ ] 5.1 In `webcompy/cli/_html.py`, collect `PluginScript` objects from `app.config.scripts` and `app._plugin_manager.scripts`, and render each through `_render_plugin_script()` from `feat-plugin-script`. **Depends on `feat-plugin-script` being merged first** — `_render_plugin_script()` must already exist in `webcompy/cli/_html.py`.

## 6. Consumer: docs_app

- [ ] 6.1 Create `docs_app/plugins.py` with `ErudaPlugin(WebComPyPlugin)` class that returns eruda `PluginScript` instances from `get_scripts()` with condition for `?debug=True`
- [ ] 6.2 Update `docs_app/webcompy_config.py` to set `plugins=["docs_app.plugins:ErudaPlugin"]` and remove `scripts` field

## 7. Testing

- [ ] 7.1 Add unit tests for `WebComPyPlugin` base class (default values, optional hooks)
- [ ] 7.2 Add unit tests for `PluginManager` discovery (valid path, invalid path, non-plugin class)
- [ ] 7.3 Add unit tests for `PluginManager` initialization (provider registration, lifecycle call order)
- [ ] 7.4 Add unit tests for router hooks (guard cancels, guard passes, error handling)
- [ ] 7.5 Add unit tests for `generate_html()` with plugin scripts
- [ ] 7.6 Add E2E test: eruda loaded via plugin on `/?debug=True`, not loaded on `/`
- [ ] 7.7 Add new E2E test file to CI matrix in `.github/workflows/ci.yml`

## 8. Type Stubs

- [ ] 8.1 Create `webcompy/plugin/__init__.pyi` with type definitions for `WebComPyPlugin`, `PluginManager`, `WebComPyPluginException`. If `webcompy/app/__init__.pyi` exists, add re-exports for these classes.
