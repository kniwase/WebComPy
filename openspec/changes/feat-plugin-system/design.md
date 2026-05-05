## Context

WebComPy has informal extension points (DI, signal callbacks, component registration, browser API) but no formal plugin system. The `feat-plugin-script` change introduces `PluginScript` for conditional JS loading, but lacks Python-side lifecycle hooks and discovery. This design adds the full plugin framework layer on top of `PluginScript`.

Constraints:
- Must work in both browser (PyScript) and server (SSG/dev server) environments
- Must not break the existing `append_script()` API
- Must use the existing DI system for service registration
- Plugins are regular Python classes in packages listed as dependencies

## Goals / Non-Goals

**Goals:**
- Provide a `WebComPyPlugin` base class with lifecycle hooks and declarative `PluginScript` / DI provider declarations
- Provide a `PluginManager` that discovers plugins from `AppConfig.plugins` paths and manages their lifecycle
- Integrate plugin initialization into `WebComPyApp.__init__()`
- Add router navigation hooks (`before_route_change`, `after_route_change`, `on_route_error`) for plugins to consume
- Collect plugin scripts in `generate_html()` for SSG and dev server output

**Non-Goals:**
- No multi-app isolation — each `WebComPyApp` manages its own plugins, but `_app_di_scope` remains a global fallback
- No PyScript-level plugin creation — orthogonal to WebComPy plugins
- No dynamic plugin loading/unloading at runtime
- No plugin marketplace or custom packaging format
- No CSP optimizations for conditional scripts

## Decisions

### Decision 1: WebComPyPlugin as a class with optional hooks

```python
class WebComPyPlugin:
    name: ClassVar[str] = ""
    version: ClassVar[str] = "0.1.0"

    @staticmethod
    def get_providers() -> dict[object, Any]: ...

    @staticmethod
    def get_scripts() -> list[PluginScript]: ...

    def on_app_init(self, app: WebComPyApp) -> None: ...
    def on_app_ready(self, app: WebComPyApp) -> None: ...
```

All lifecycle hooks are optional (default no-op). `get_providers()` and `get_scripts()` are static methods (called before instantiation) so the manager can collect declarations without creating instances.

`get_providers()` returns a dict of `{key: factory_or_value}`, compatible with `DIScope.provide()`. Callable values are treated as lazy factories.

Alternatives considered:
- `get_scripts` as instance method → would require instantiation before script collection, adding unnecessary lifecycle complexity
- Decorator-based registration (`@plugin`) → less structured, harder to discover capabilities

### Decision 2: PluginManager as a standalone class per-app

```python
class PluginManager:
    def __init__(self, app: WebComPyApp): ...
    def discover(self, plugin_paths: list[str]): ...
    def init_all(self): ...
    def call_on_app_ready(self, app: WebComPyApp): ...
    @property
    def scripts(self) -> list[PluginScript]: ...
```

`PluginManager` is created per-app instance. It:
1. Stores the app reference at init time
2. Discovers plugins: Splits each `"module:Class"` path, `importlib.import_module`s, validates the class is a `WebComPyPlugin`
3. Collects providers from `get_providers()` and registers them with `app.di_scope` during `init_all()`
4. Instantiates each plugin and calls `on_app_init(app)` during `init_all()`
5. Exposes `scripts` property that collects `get_scripts()` from all plugins
6. Provides `call_on_app_ready(app)` that calls `on_app_ready` on all plugin instances

**Important**: `discover()` and `init_all()` must be called after the app's DI scope is set up, since `init_all()` registers providers into it. The correct call order in `WebComPyApp.__init__()` is documented in Decision 4.

Alternatives considered:
- Singleton PluginManager → conflicts with multi-app use cases (SSG renders per-route)
- Class-level registration dict → less explicit; import-time side effects are harder to reason about

### Decision 3: Router hooks through callable lists

```python
class Router:
    def __init__(self, ...):
        ...
        # Instance attributes (NOT class-level) — each Router has its own hooks
        self.before_route_change: list[Callable[[str, str], bool | None]] = []
        self.after_route_change: list[Callable[[str], None]] = []
        self.on_route_error: list[Callable[[Exception], bool]] = []
```

Plugins append callbacks to these lists. `before_route_change` returns `False` to cancel navigation (e.g., authentication guard). `on_route_error` callbacks receive the exception and return `True` to suppress propagation (handled), or `False`/`None` to allow the exception to propagate normally.

Callbacks are dispatched:
- `before_route_change`: In `Location.__set_path__()` before updating the signal value. If ANY callback returns `False`, navigation is cancelled. Remaining callbacks are NOT called (short-circuit). `after_route_change` is NOT called when navigation is cancelled.
- `after_route_change`: In `Location.__set_path__()` after updating the signal value, only if navigation was not cancelled.
- `on_route_error`: The `Router` SHALL wrap the route resolution logic in a try/except and dispatch any caught exceptions to `on_route_error` callbacks. If a callback returns `True`, the exception is suppressed. If all callbacks return `False` or `None`, the exception propagates.

This is a minimal addition — no full middleware chain, no async support. Sufficient for initial plugin use cases.

Alternatives considered:
- Event bus / pub-sub → over-engineered for the initial scope
- Async `await` hooks → PyScript's synchronous execution model makes this complex; deferred

### Decision 4: Plugin initialization in WebComPyApp.__init__()

```python
# In WebComPyApp.__init__():
self._di_scope = DIScope()
...
self._router = router  # store before PluginManager init so plugins can access it
self._plugin_manager = PluginManager(self)
if self._config.plugins:
    self._plugin_manager.discover(self._config.plugins)
    self._plugin_manager.init_all()
```

Plugins are initialized after the DI scope and component store are set up but before `AppDocumentRoot` is created. The router instance is stored on the app (`self._router`) before `init_all()` so plugins can call `app.router.before_route_change.append(...)` during `on_app_init()`. This ensures:
- Plugins can register DI providers before any component tries to inject them
- Plugins can hook into the router (if one exists) before route resolution starts
- `generate_html()` can collect plugin scripts before HTML generation

### Decision 5: generate_html() collects plugin scripts from both sources

```python
# In generate_html():
scripts_head_extra: list[PluginScript] = []
scripts_body_extra: list[PluginScript] = []

# ... existing script collection ...

# Scripts from AppConfig.scripts (direct PluginScript)
for ps in app.config.scripts:
    (scripts_head_extra if ps.in_head else scripts_body_extra).append(ps)

# Scripts from PluginManager (plugin classes)
for ps in app._plugin_manager.scripts:
    (scripts_head_extra if ps.in_head else scripts_body_extra).append(ps)

# Render each PluginScript through the helper
for ps in scripts_head_extra:
    scripts_head.append(*_render_plugin_script(ps))
for ps in scripts_body_extra:
    scripts_body.append(*_render_plugin_script(ps))
```

Both `app.config.scripts` (direct PluginScript descriptors) and `app._plugin_manager.scripts` (from plugin classes) are collected as full `PluginScript` objects and rendered through `_render_plugin_script()` from `feat-plugin-script`. This helper handles converting `PluginScript` instances with conditions into wrapper `<script>` tags and statically rendering those without conditions.

## Risks / Trade-offs

- **[Medium] Router hooks are synchronous only** → Navigation guards run synchronously. Guards that need async checks (e.g., API call) must use blocking patterns or defer authorization to component rendering. Mitigation: Document this limitation. Async hooks can be added later without breaking the sync API.
- **[Low] Plugin discovery uses importlib at runtime** → `importlib.import_module(module_path)` in the browser requires the module to be bundled in the app wheel. Mitigation: Already handled by the dependency bundling pipeline (`LOCAL_PURE_PYTHON` packages are always bundled).
- **[Low] Plugin ordering is declaration order** → Plugins are initialized in the order listed in `AppConfig.plugins`. Dependencies between plugins are not enforced. Mitigation: Document that plugin order matters. Inter-plugin dependency management can be added later.
- **[Low] One plugin manager per app** → SSG with multiple concurrent renders could theoretically conflict. Mitigation: Each SSG render uses `with app.di_scope:`, and plugins are initialized once. This is safe because plugin state is stored per-instance.
- **[Low] WebComPyPluginException location** → The exception class is defined in `webcompy.plugin` (alongside `WebComPyPlugin` and `PluginManager`), not in the shared `webcompy.exception` module. This keeps the plugin package self-contained.

## Open Questions

1. **Should `on_app_ready` be called from `run()` or `_render()`?** → Recommend calling from `run()` before the first `_render()` call. This gives plugins access to the DOM mount point and browser APIs before any component renders.
2. **Should router hooks be on `Router` or a separate `RouterHookRegistry`?** → Recommend keeping on `Router` directly for simplicity. A separate registry can be extracted later if the API grows.
