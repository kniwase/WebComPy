# Proposal: Lazy Routing — Deferred Module Import and Route Preloading

## Summary

Add lazy route import capability to the Router so that page component modules are imported only when their route is first matched, reducing the initial Python import burden at startup. This is implemented via a new `lazy()` helper function that wraps an absolute module path string into a `LazyComponentGenerator` (a `ComponentGenerator` subclass). After the initial page renders, the Router automatically preloads remaining lazy routes so that subsequent navigation is instant. Additionally, `RouterLink` preloading on hover (mouseenter) speculatively imports the target route's module before the user clicks.

## Motivation

When a WebComPy app starts, all page modules referenced in the Router are imported immediately — even for pages the user won't visit in the current session. In a PyScript/Pyodide environment where `import` can be expensive (disk I/O + module evaluation + dependency resolution), this adds unnecessary startup delay.

For example, the docs_src app imports 6+ page modules at startup, each containing component definitions, reactive state, and potentially heavy logic. If the user only visits the home page, all other page modules were loaded for nothing.

The current Router API requires passing `ComponentGenerator` objects directly:

```python
router = Router(
    {"path": "/", "component": HomePage},        # ← HomePage imported immediately
    {"path": "/docs", "component": DocsPage},     # ← DocsPage imported immediately
    {"path": "/demo", "component": DemoPage},      # ← DemoPage imported immediately
)
```

Lazy routing solves this by deferring imports to first use. Since Python `import` in Pyodide is synchronous and fast for modules already in the loaded wheel, once a lazy route is resolved, all subsequent navigations to that route are instant.

Auto-preload (importing all remaining lazy routes after the initial page renders) ensures that the user benefits from fast startup without paying the cost of on-demand imports for subsequent navigation.

## Known Issues Addressed

None directly (this is a new capability).

## Non-goals

- This does not implement JavaScript-style code splitting (Pyodide loads all code from wheels at startup; lazy routing only defers Python `import` within the loaded wheel).
- This does not implement route guards or before/after navigation hooks.
- This does not implement nested or lazy-loaded route configurations.
- This does not add route-level code splitting at the wheel level (that would require multiple wheels per route).
- This does not implement shell/loading placeholder rendering for lazy routes (Python `import` is synchronous in Pyodide, so there is no viable window for shell display between navigation and render).

## Dependencies

- **Informed by** `feat/hydration-measurement` — profiling data will show the time saved by deferring imports.
- **Informs** `feat/hydration-full` — fewer components to hydrate on initial load means faster hydration.

## Design

### Part 1: Lazy Route Import via `lazy()` Helper

#### API

A new function `lazy()` in `webcompy.router` that creates a deferred `ComponentGenerator`:

```python
from webcompy.router import lazy

router = Router(
    {"path": "/", "component": HomePage},                                    # eager (existing)
    {"path": "/docs", "component": lazy("myapp.pages.docs:DocsPage", __file__)},    # lazy
    {"path": "/demo", "component": lazy("myapp.pages.demo:DemoPage", __file__)},   # lazy
)
```

#### `lazy()` Function Signature

```python
def lazy(
    import_path: str,
    caller_file: str,
) -> ComponentGenerator:
    """Create a lazy ComponentGenerator that defers module import until first use.
    
    Args:
        import_path: Absolute dotted module path and attribute name,
                      e.g. "myapp.pages.docs:DocsPage"
        caller_file: The __file__ of the calling module, used for
                      validation and error messages.
    
    Raises:
        WebComPyRouterException: If import_path format is invalid.
    """
```

The `import_path` parameter must be an **absolute** dotted module path (e.g., `"myapp.pages.docs:DocsPage"`, not `".pages.docs:DocsPage"`). This avoids brittle `__file__`-to-package-name derivation that would break across Pyodide, SSG, and development environments. The `caller_file` parameter is used for validation and error messages.

#### Validation

`lazy()` validates the `import_path` format at call time:

```python
def lazy(import_path: str, caller_file: str) -> ComponentGenerator:
    if ":" not in import_path:
        raise WebComPyRouterException(
            f"lazy() import_path must be 'module:Attribute' format, got: {import_path!r}"
        )
    module_path, attr_name = import_path.rsplit(":", 1)
    if not module_path or not attr_name:
        raise WebComPyRouterException(
            f"lazy() import_path must have non-empty module and attribute, got: {import_path!r}"
        )
    if not caller_file:
        raise WebComPyRouterException("lazy() caller_file must not be empty")
    return LazyComponentGenerator(import_path, caller_file)
```

Module existence and attribute validation happen at `_resolve()` time (runtime), not at `lazy()` call time, because the module may not be importable until the wheel is installed in Pyodide.

#### Implementation

Before implementing `LazyComponentGenerator`, `ComponentGenerator`'s name-mangled private attributes (`__name`, `__id`, `__style`, `__registered`, `__component_def`) must be renamed to single-underscore variants (`_name`, `_id`, etc.) to allow `LazyComponentGenerator` to access and delegate to them properly.

```python
class LazyComponentGenerator(ComponentGenerator):
    _import_path: str
    _caller_file: str
    _resolved: ComponentGenerator | None

    def __init__(self, import_path: str, caller_file: str) -> None:
        # Parse import_path for the component name (used before resolution)
        self._import_path = import_path
        self._caller_file = caller_file
        self._resolved = None
        # Initialize minimal ComponentGenerator fields without calling super().__init__()
        # We cannot call super().__init__() because it requires a component definition function
        # which we don't have yet (it will be resolved lazily).
        self._name = import_path.rsplit(":", 1)[-1]  # Use attribute name as display name
        self._id = generate_id(self._name)
        self._style = {}
        self._component_def = None  # Will be set on resolution
        self._registered = False

    def _resolve(self) -> ComponentGenerator:
        if self._resolved is None:
            module_path, attr_name = self._import_path.rsplit(":", 1)
            module = importlib.import_module(module_path)
            resolved = getattr(module, attr_name)
            if not isinstance(resolved, ComponentGenerator):
                raise WebComPyRouterException(
                    f"'{self._import_path}' is not a ComponentGenerator"
                )
            self._resolved = resolved
            # Delegate all attributes to the resolved generator
            self._component_def = resolved._component_def
            self._name = resolved._name
            self._id = resolved._id
            self._style = resolved._style
            self._registered = resolved._registered
            resolved._try_register()
        return self._resolved

    def _preload(self) -> None:
        """Import the module without rendering."""
        self._resolve()

    def __call__(self, props, *, slots=None):
        resolved = self._resolve()
        return resolved(props, slots=slots)

    def __getattr__(self, name: str):
        return getattr(self._resolve(), name)

    @property
    def scoped_style(self):
        return self._resolve().scoped_style

    @scoped_style.setter
    def scoped_style(self, value):
        self._resolve().scoped_style = value
```

**Key design decisions:**

- `super().__init__()` is not called because it requires a `component_def` function that doesn't exist yet. Instead, minimal fields are initialized manually.
- After `_resolve()`, all internal attributes are replaced with the resolved generator's values. This ensures `scoped_style`, `_try_register()`, and `ComponentStore` iteration all work correctly.
- `_try_register()` is called on the resolved generator, not on `self`, because the resolved generator is the real `ComponentGenerator` with the actual component definition.

#### Eager vs. Lazy Behavior Comparison

```
┌───────────────────────────────────────────────────────────────┐
│  Eager (existing):                                            │
│                                                               │
│  # router.py                                                  │
│  from .pages.docs import DocsPage     # ← import at startup  │
│  router = Router(                                             │
│      {"path": "/docs", "component": DocsPage},               │
│  )                                                            │
│  → DocPage module evaluated immediately                      │
│  → ComponentGenerator created immediately                     │
│  → ComponentStore registration immediate                     │
│                                                               │
│  Lazy (proposed):                                             │
│                                                               │
│  # router.py                                                  │
│  router = Router(                                             │
│      {"path": "/docs", "component": lazy("myapp.pages.docs:DocsPage", __file__)},│
│  )                                                            │
│  → No import at startup                                       │
│  → LazyComponentGenerator created (lightweight wrapper)       │
│  → On first navigation to /docs:                              │
│    1. importlib.import_module("myapp.pages.docs")            │
│    2. Resolve DocsPage attribute                               │
│    3. Register with ComponentStore                             │
│    4. Render the component                                    │
└───────────────────────────────────────────────────────────────┘
```

### Part 2: Auto-Preload After Initial Render

After the initial page renders, the Router automatically imports all remaining lazy routes so that subsequent navigation is instant. This eliminates the user-facing cost of lazy imports while preserving the startup performance benefit.

#### How Auto-Preload Works

```python
class Router:
    def preload_lazy_routes(self) -> None:
        """Preload all unresolved lazy routes."""
        from webcompy._browser._modules import browser
        for route in self.__routes__:
            component = route[3]  # RouteType[3] = ComponentGenerator
            if isinstance(component, LazyComponentGenerator) and component._resolved is None:
                if browser:
                    # Browser: schedule after current render
                    def _do_preload(c=component):
                        c._preload()
                    browser.window.setTimeout(_do_preload, 0)
                else:
                    # SSG: resolve immediately (all pages must render)
                    component._preload()
```

`RouterView._on_set_parent()` calls `router.preload_lazy_routes()` after the initial render, giving the browser time to paint the first page before importing remaining modules.

```python
class RouterView(Element):
    def _on_set_parent(self):
        # ... existing rendering logic ...
        # Schedule preload of remaining lazy routes
        self._router.preload_lazy_routes()
```

#### Auto-Preload Timeline

```
┌───────────────────────────────────────────────────┐
│  t=0ms    app.run() starts                        │
│  t=50ms   Initial route resolved (lazy or eager)  │
│  t=50ms   Initial page rendered                   │
│  t=50ms   preload_lazy_routes() called            │
│  t=50ms   setTimeout(0) for each unresolved route │
│  t=200ms  All lazy routes preloaded               │
│                                                   │
│  → Subsequent navigation: instant (already in mem)│
└───────────────────────────────────────────────────┘
```

#### Preload Configuration

`Router.__init__` gains a `preload` parameter:

```python
class Router:
    def __init__(
        self,
        *pages: RouterPage,
        default: ComponentGenerator | None = None,
        mode: Literal["hash", "history"] = "hash",
        base_url: str = "",
        preload: bool = True,
    ) -> None:
```

- `preload=True` (default): Auto-preload all lazy routes after initial render.
- `preload=False`: Only import lazy routes on navigation (no auto-preload).

### Part 3: Route Preloading via RouterLink Hover

To further reduce perceived navigation latency, `RouterLink` preloads (resolves) the target route's lazy component when the user hovers over the link.

#### Implementation

`Router` gains a `_get_component_for_path()` method used by `RouterLink`:

```python
class Router:
    def _get_component_for_path(self, path: str) -> ComponentGenerator | None:
        """Return the ComponentGenerator for the given path, or None if no match."""
        clean_path = path.strip("/")
        for route in self.__routes__:
            _, matcher, _, component, _ = route  # Unpack all 5 fields
            if matcher(clean_path):
                return component
        return None
```

`RouterLink` adds a `@mouseenter` handler:

```python
def on_mouseenter(_ev=None):
    target = self._router._get_component_for_path(to_path)
    if isinstance(target, LazyComponentGenerator):
        target._preload()
```

This complements auto-preload: if the user hovers before auto-preload completes, the target route is imported immediately.

### Part 4: SSG Compatibility

For static site generation, all lazy routes must be eagerly resolved so that `AppDocumentRoot._render_html()` can produce correct HTML output. This works naturally:

1. SSG sets the path via `Router.__set_path__()`.
2. `SwitchElement._refresh()` is triggered via signal.
3. `LazyComponentGenerator.__call__()` calls `_resolve()`, which synchronously imports the module.
4. Additionally, `Router.preload_lazy_routes()` resolves all remaining lazy routes immediately in non-browser environments (no `setTimeout`), ensuring all pages render correctly.

### Part 5: ComponentGenerator Attribute Rename

`ComponentGenerator`'s name-mangled private attributes are renamed to single-underscore variants to allow `LazyComponentGenerator` to access and delegate to them:

| Old Name | New Name |
|---|---|
| `__name` | `_name` |
| `__id` | `_id` |
| `__style` | `_style` |
| `__registered` | `_registered` |
| `__component_def` | `_component_def` |

Similarly, `ComponentStore.__components` becomes `ComponentStore._components`.

This is a pure refactor with no behavioral change — no external code accesses these attributes via the name-mangled form.

### Migration Path

Existing code using eager imports continues to work without changes. The `lazy()` function is opt-in:

```python
# Before (still works):
from .pages.home import HomePage
from .pages.docs import DocsPage
router = Router(
    {"path": "/", "component": HomePage},
    {"path": "/docs", "component": DocsPage},
)

# After (opt-in lazy):
from .pages.home import HomePage  # home is eager (initial page)
router = Router(
    {"path": "/", "component": HomePage},
    {"path": "/docs", "component": lazy("myapp.pages.docs:DocsPage", __file__)},
    {"path": "/demo", "component": lazy("myapp.pages.demo:DemoPage", __file__)},
)
```

Recommended pattern: Keep the initial/home route eager (it's needed at startup anyway) and make all other routes lazy.

## Specs Affected

- `router` — adds `lazy()` function; adds `LazyComponentGenerator`; adds route auto-preloading after initial render; adds `RouterLink` hover preloading; adds `preload` parameter to `Router`
- `components` — no changes needed (`LazyComponentGenerator` is a `ComponentGenerator` subclass, compatible with existing APIs)