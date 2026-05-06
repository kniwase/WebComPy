## Why

WebComPy currently has no formal plugin system. The DI (provide/inject), signal callbacks (on_after_updating), component registration (ComponentStore), and browser API (webcompy.browser) provide informal extension points, but there is no official API for third-party Python packages to integrate with the framework's lifecycle, register custom behavior, or hook into core events like route changes. The `PluginScript` dataclass from `feat-plugin-script` provides conditional JS loading, but lacks the Python-side lifecycle and discovery mechanisms needed for rich integrations like debug toolbars, authentication systems, or analytics.

PyScript has its own plugin system (JS-based hooks on `hooks.main` / `hooks.worker`), but this operates at the interpreter level and is orthogonal to WebComPy's component and router layers.

## What Changes

- **Add `webcompy/plugin/` package**: New framework module containing the plugin system implementation.
- **Add `WebComPyPlugin` base class**: Plugin classes extend this to declare lifecycle hooks (`on_app_init`, `on_app_ready`), provide DI services (`get_providers()`), and expose `PluginScript` instances (`scripts`).
- **Add `PluginManager`**: Discovers plugins from `AppConfig.plugins`, manages lifecycle initialization, collects scripts for HTML generation.
- **Add `AppConfig.plugins` field**: A `list[str]` of absolute module paths (e.g., `"myapp.plugins:ErudaPlugin"`) for plugin discovery via `importlib`.
- **Extend `WebComPyApp.__init__()`**: Call `PluginManager.init_all(self)` after DI scope setup to initialize all registered plugins.
- **Add router navigation hooks**: The `Router` SHALL support `before_route_change` and `after_route_change` callbacks, enabling plugins to implement guards and analytics.
- **Integrate with `generate_html()`**: Collect `PluginScript` instances from plugins via `PluginManager` and include them in the generated HTML.

## Known Issues Addressed

- Addresses "No plugin system (noted in README ToDo)" — this provides the full Python-side plugin framework.

## Non-goals

- **No multi-app isolation fix** — the `_app_di_scope` / `_app_instance` module-level fallback limitation remains. Each `WebComPyApp` handles its own plugin instances, but true multi-app isolation is a separate concern.
- **No PyScript-level plugin creation** — WebComPy plugins operate in the Python layer, orthogonal to PyScript's JS-based plugin hooks.
- **No hot-reload of plugins** — plugins are initialized once at app startup. Dynamic plugin loading/unloading at runtime is not supported.
- **No plugin marketplace or distribution format** — plugins are regular Python packages listed as dependencies. No new packaging format is introduced.
- **No bundling optimizations for plugin scripts** — CSP concerns for conditional scripts are deferred.

## Capabilities

### New Capabilities
- `plugin-system`: The full plugin framework — `WebComPyPlugin` base class, `PluginManager`, lifecycle hooks, and DI integration. Builds on `PluginScript` from `feat-plugin-script`.
- `router-hooks`: Navigation guards and lifecycle callbacks on the Router (`before_route_change`, `after_route_change`, `on_route_error`).

### Modified Capabilities
- `app-config`: `AppConfig` gains a `plugins: list[str]` field (default `[]`) for declarative plugin discovery.
- `app`: `WebComPyApp.__init__()` invokes `PluginManager.init_all(self)` as part of the bootstrap sequence.

## Impact

- **New module**: `webcompy/plugin/` — `__init__.py`, `_manager.py`, `_plugin.py`
- **Affected code**:
  - `webcompy/app/_config.py`: Add `plugins` field to `AppConfig`
  - `webcompy/app/_app.py`: Call `PluginManager.init_all()` in `__init__()`
  - `webcompy/app/__init__.py`: Export `PluginManager`, `WebComPyPlugin`
  - `webcompy/cli/_html.py`: Collect scripts from `PluginManager`
  - `webcompy/router/_router.py`: Add navigation guard support
  - `webcompy/router/_change_event_handler.py`: Add hook dispatch
- **Consumer change**:
  - `docs_app/`: Replace eruda `PluginScript` config with `ErudaPlugin` class (example migration)
- **No new external dependencies**
