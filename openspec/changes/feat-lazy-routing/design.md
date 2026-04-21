# Design: Lazy Routing — Deferred Module Import and Route Preloading

## Design Decisions

### D1: `lazy()` creates a deferred `ComponentGenerator` wrapper
The `lazy()` function returns a `LazyComponentGenerator` that defers `importlib.import_module` until first use. This wrapper implements the `ComponentGenerator` interface so the existing `Router` works without modification.

### D2: `caller_file` parameter resolves relative imports
Since the working directory may differ between server and Pyodide/browser, `lazy()` accepts `caller_file` (passed as `__file__`) to resolve relative imports. For example:
```python
lazy("pages.docs:DocsPage", __file__)
```
If `__file__` is `/app/router.py`, `caller_package` is `"app"`, and the absolute module becomes `"app.pages.docs"`.

### D3: Shell component is optional
If the user passes `shell=None`, `LazyComponentGenerator.__call__()` resolves and renders synchronously (blocking until the module is imported). The Python `import` within a pre-loaded wheel is fast enough for most cases. The shell is provided for rare heavy initialization or future async loading.

### D4: RouterLink hover preloading is opportunistic
On `mouseenter`, `RouterLink` checks whether the target route uses a `LazyComponentGenerator`. If so, it calls `_preload()` (which calls `_resolve()` without rendering). This reduces perceived navigation latency. If the module is already loaded, `_preload()` is a no-op.

### D5: SSG eagerly resolves lazy routes
For static generation, `LazyComponentGenerator._resolve()` is called before rendering so the full component tree is available. The existing `Router.__set_path__()` → `SwitchElement._refresh()` path triggers resolution naturally.

## Architecture

### Lazy Component Resolution Flow

```
Startup (no lazy import):
═════════════════════════
  router = Router(
      {"path": "/docs", "component": lazy("pages.docs:DocsPage", __file__)},
  )
  → LazyComponentGenerator created (lightweight)
  → No import

First navigation to /docs:
═══════════════════════════
  Router.match("/docs")
  → Returns LazyComponentGenerator
  → SwitchElement selects it
  → LazyComponentGenerator.__call__(props)
     → _resolve()
        → importlib.import_module("pages.docs", package=caller_package)
        → getattr(module, "DocsPage")
        → DocsPage._try_register() in ComponentStore
        → _resolved ← DocsPage
     → _resolved(props)  (renders component)
  → DOM updated

RouterLink hover preloading:
════════════════════════════
  mouseenter
  → _get_route_generator("/docs")
  → isinstance(LazyComponentGenerator)
  → _preload()
     → _resolve() (same as above, but without rendering)
  → Module loaded in background
```

### `LazyComponentGenerator` Class Design

```python
class LazyComponentGenerator(ComponentGenerator):
    _import_path: str
    _caller_file: str
    _resolved: ComponentGenerator | None
    _shell: ComponentGenerator | None

    def __init__(
        self,
        import_path: str,
        caller_file: str,
        shell: ComponentGenerator | None = None,
    ) -> None:
        self._import_path = import_path
        self._caller_file = caller_file
        self._resolved = None
        self._shell = shell
        # Do NOT call super().__init__() — defer ComponentGenerator creation

    def _resolve(self) -> ComponentGenerator:
        if self._resolved is None:
            module_path, attr_name = self._import_path.rsplit(":", 1)
            caller_path = pathlib.Path(self._caller_file)
            # Compute caller package from file path
            # e.g. /app/pages/about.py → caller_package = "app.pages"
            # e.g. /app/router.py     → caller_package = "app"
            caller_package = ".".join(caller_path.parent.parts)
            # Resolve module
            module = importlib.import_module(module_path, package=caller_package)
            self._resolved = getattr(module, attr_name)
            if not isinstance(self._resolved, ComponentGenerator):
                raise WebComPyRouterException(
                    f"'{self._import_path}' is not a ComponentGenerator"
                )
            self._resolved._try_register()
        return self._resolved

    def _preload(self) -> None:
        """Import the module without rendering."""
        self._resolve()

    def __call__(self, props, *, slots=None):
        return self._resolve()(props, slots=slots)

    def __getattr__(self, name: str):
        return getattr(self._resolve(), name)

    @property
    def scoped_style(self):
        return self._resolve().scoped_style

    @scoped_style.setter
    def scoped_style(self, value):
        self._resolve().scoped_style = value
```

### Shell Rendering Integration

If `LazyComponentGenerator._shell` is set and `_resolved` is None, `Router._get_elements_generator()` returns the shell component instead of the real component:

```python
def _get_elements_generator(self, args):
    ...
    if match:
        component = args[3]  # RouteType[3] = ComponentGenerator
        if isinstance(component, LazyComponentGenerator):
            if component._shell and not component._resolved:
                return (match, lambda: component._shell(None))
            else:
                return (match, lambda: component(props))
        else:
            return (match, lambda: component(props))
```

When the lazy component later resolves, a signal change triggers `SwitchElement._refresh()`, which then re-renders with the real component (because `_resolved` is now set).

### RouterLink Preloading

```python
@define_component
def RouterLink(context):
    target_path = context.props.to

    def on_mouseenter(_ev=None):
        target_generator = _get_route_generator(target_path)
        if isinstance(target_generator, LazyComponentGenerator):
            target_generator._preload()

    return html.A(
        {"@click": navigate, "@mouseenter": on_mouseenter},
        context.slots("default"),
    )
```

### SSG Eager Resolution

SSG works naturally because `Router.__set_path__()` triggers `SwitchElement._refresh()`, which calls the component generator. `LazyComponentGenerator.__call__()` calls `_resolve()`, which eagerly loads the module:

```python
# In generate_static_site
app.__component__.__set_path__("/docs")  # triggers Router match
# SwitchElement._refresh() calls lazy_component.__call__(props)
# → _resolve() imports the module → HTML rendered correctly
```

## Risk: `importlib` Resolution in Pyodide

Pyodide uses Emscripten's virtual filesystem where `__file__` and `os.getcwd()` may differ from the host Python environment. The `caller_package` resolution assumes that `__file__` parent directories map directly to Python namespaces. If Pyodide mounts packages at different paths, `importlib.import_module(module_path, package=caller_package)` could fail.

Mitigation:
- Use absolute dotted import paths in `lazy()` rather than relative dotted paths (e.g., `"myapp.pages.docs:DocsPage"` instead of `".pages.docs:DocsPage"`).
- The `caller_package` is derived from `__file__` to ensure the absolute package name is correct relative to the file's location.

## Rollback Path

If lazy routing introduces import resolution issues:
1. Keep eager imports for all routes (migration path: replace `lazy(...)` with direct `from x import y`).
2. `LazyComponentGenerator` remains usable, but routes can be made eager at user discretion.

## Performance Impact

For `docs_src` (6 page modules):
- **Before:** All 6 modules imported at startup.
- **After (with lazy):** Only the home page module is imported at startup; other 5 deferred. On a single-page visit, startup import time is reduced by ~80% (5/6 of modules deferred).

If `wheel-split` is also implemented and the app wheel is pre-cached in the browser, repeated visits may benefit from the cached app wheel but still enjoy reduced import time.

## Dependencies

- **Informed by:** `feat/hydration-measurement` — profiling data shows time saved.
- **Informs:** `feat/hydration-full` — lazy routes reduce the number of components to hydrate.

## Specs to Update

- `openspec/specs/router/spec.md` — add `lazy()` function, `LazyComponentGenerator`, shell rendering, and RouterLink preloading requirements.
- `openspec/specs/components/spec.md` — mention `LazyComponentGenerator` as a compatible `ComponentGenerator` subclass.
