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
    @property
    def scripts(self) -> list[PluginScript]: ...
```

`PluginManager` is created per-app instance. It:
1. Discovers plugins: Splits each `"module:Class"` path, `importlib.import_module`s, validates the class is a `WebComPyPlugin`
2. Collects providers from `get_providers()` and registers them with `app.di_scope`
3. Instantiates each plugin and calls `on_app_init(app)`
4. Exposes `scripts` property that collects `get_scripts()` from all plugins

Alternatives considered:
- Singleton PluginManager → conflicts with multi-app use cases (SSG renders per-route)
- Class-level registration dict → less explicit; import-time side effects are harder to reason about

### Decision 3: Router hooks through callable lists

```python
class Router:
    before_route_change: list[Callable[[str, str], bool | None]] = []  # (from_path, to_path) -> False to cancel
    after_route_change: list[Callable[[str], None]] = []  # (path) -> None
    on_route_error: list[Callable[[Exception], None]] = []  # (error) -> None
```

Plugins append callbacks to these lists. `before_route_change` returns `False` to cancel navigation (e.g., authentication guard).

Callbacks are dispatched in `Location.__set_path__()` before updating the signal value (`before_route_change`) and after (`after_route_change`).

This is a minimal addition — no full middleware chain, no async support. Sufficient for initial plugin use cases.

Alternatives considered:
- Event bus / pub-sub → over-engineered for the initial scope
- Async `await` hooks → PyScript's synchronous execution model makes this complex; deferred

### Decision 4: Plugin initialization in WebComPyApp.__init__()

```python
# In WebComPyApp.__init__():
self._di_scope = DIScope()
...
self._plugin_manager = PluginManager(self)
if self._config.plugins:
    self._plugin_manager.discover(self._config.plugins)
    self._plugin_manager.init_all()
```

Plugins are initialized after the DI scope and component store are set up but before `AppDocumentRoot` is created. This ensures:
- Plugins can register DI providers before any component tries to inject them
- Plugins can hook into the router (if one exists) before route resolution starts
- `generate_html()` can collect plugin scripts before HTML generation

### Decision 5: generate_html() collects plugin scripts

```python
# In generate_html():
scripts_head: Scripts = []
scripts_body: Scripts = []

# ... existing script collection ...

# Plugin scripts (from PluginScript descriptor)
for ps in app._plugin_manager.scripts:
    if ps.in_head:
        scripts_head.append((ps.attrs, ps.script))
    else:
        scripts_body.append((ps.attrs, ps.script))
```

The existing `_render_conditional_script()` from `feat-plugin-script` handles converting `PluginScript` with conditions into wrapper `<script>` tags. The `scripts_head`/`scripts_body` lists naturally extend to include plugin scripts.

## Risks / Trade-offs

- **[Medium] Router hooks are synchronous only** → Navigation guards run synchronously. Guards that need async checks (e.g., API call) must use blocking patterns or defer authorization to component rendering. Mitigation: Document this limitation. Async hooks can be added later without breaking the sync API.
- **[Low] Plugin discovery uses importlib at runtime** → `importlib.import_module(module_path)` in the browser requires the module to be bundled in the app wheel. Mitigation: Already handled by the dependency bundling pipeline (`LOCAL_PURE_PYTHON` packages are always bundled).
- **[Low] Plugin ordering is declaration order** → Plugins are initialized in the order listed in `AppConfig.plugins`. Dependencies between plugins are not enforced. Mitigation: Document that plugin order matters. Inter-plugin dependency management can be added later.
- **[Low] One plugin manager per app** → SSG with multiple concurrent renders could theoretically conflict. Mitigation: Each SSG render uses `with app.di_scope:`, and plugins are initialized once. This is safe because plugin state is stored per-instance.

## Open Questions

1. **Should `on_app_ready` be called from `run()` or `_render()`?** → Recommend calling from `run()` before the first `_render()` call. This gives plugins access to the DOM mount point and browser APIs before any component renders.
2. **Should router hooks be on `Router` or a separate `RouterHookRegistry`?** → Recommend keeping on `Router` directly for simplicity. A separate registry can be extracted later if the API grows.
