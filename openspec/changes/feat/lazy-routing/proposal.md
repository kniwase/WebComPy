# Proposal: Lazy Routing — Deferred Module Import and Route Preloading

## Summary

Add lazy route import capability to the Router so that page component modules are imported only when their route is first matched, reducing the initial Python import burden at startup. This is implemented via a new `lazy` helper function that wraps a module path string into a `ComponentGenerator`. Additionally, add `RouterLink` preloading on hover (mouseenter) to speculatively import the target route's module before the user clicks, reducing perceived navigation latency. Finally, add a component "shell" rendering mode to show a loading placeholder while the lazy component's module is being imported.

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

## Known Issues Addressed

None directly (this is a new capability).

## Non-goals

- This does not implement JavaScript-style code splitting (Pyodide loads all code from wheels at startup; lazy routing only defers Python `import` within the loaded wheel).
- This does not implement route guards or before/after navigation hooks.
- This does not implement nested or lazy-loaded route configurations.
- This does not add route-level code splitting at the wheel level (that would require multiple wheels per route).

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
    {"path": "/docs", "component": lazy("pages.docs:DocsPage", __file__)},    # lazy
    {"path": "/demo", "component": lazy("pages.demo:DemoPage", __file__)},   # lazy
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
        import_path: Dotted module path and attribute name, e.g. "pages.docs:DocsPage"
        caller_file: The __file__ of the calling module, used to resolve
                     relative imports. This ensures stable resolution regardless
                     of the working directory.
    """
```

The `caller_file` parameter (passed as `__file__`) is critical for resolving relative imports. In Pyodide, the working directory may differ from the development environment, so absolute module resolution via `__file__` ensures correctness.

#### Implementation

```python
class LazyComponentGenerator(ComponentGenerator):
    _import_path: str
    _caller_file: str
    _resolved: ComponentGenerator | None

    def __init__(self, import_path: str, caller_file: str) -> None:
        self._import_path = import_path
        self._caller_file = caller_file
        self._resolved = None
        # Don't call super().__init__() — defer ComponentGenerator creation

    def _resolve(self) -> ComponentGenerator:
        if self._resolved is None:
            module_path, attr_name = self._import_path.rsplit(":", 1)
            # Derive the full package path from the caller's __file__.
            # e.g. __file__ = "/app/pages/about.py" → package = "pages.about"
            # This works for both top-level and nested packages.
            caller_path = pathlib.Path(self._caller_file)
            caller_package = ".".join(caller_path.parent.parts)
            module = importlib.import_module(module_path, package=caller_package)
            self._resolved = getattr(module, attr_name)
            if not isinstance(self._resolved, ComponentGenerator):
                raise WebComPyRouterException(
                    f"'{self._import_path}' is not a ComponentGenerator"
                )
            # Register with the active ComponentStore
            self._resolved._try_register()
        return self._resolved

    def __call__(self, props, *, slots=None):
        return self._resolve()(props, slots=slots)

    def __getattr__(self, name: str):
        """Delegate all attribute access to the resolved ComponentGenerator."""
        return getattr(self._resolve(), name)

    @property
    def scoped_style(self):
        return self._resolve().scoped_style

    @scoped_style.setter
    def scoped_style(self, value):
        self._resolve().scoped_style = value
```

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
│      {"path": "/docs", "component": lazy("pages.docs:DocsPage", __file__)},│
│  )                                                            │
│  → No import at startup                                       │
│  → LazyComponentGenerator created (lightweight wrapper)       │
│  → On first navigation to /docs:                              │
│    1. importlib.import_module("pages.docs")                   │
│    2. Resolve DocsPage attribute                               │
│    3. Register with ComponentStore                             │
│    4. Render the component                                    │
└───────────────────────────────────────────────────────────────┘
```

### Part 2: Route Preloading via RouterLink Hover

To reduce perceived navigation latency, `RouterLink` should preload (resolve) the target route's lazy component when the user hovers over the link.

#### Implementation

```python
# In RouterLink's component definition
@define_component
def RouterLink(context):
    target_path = context.props.to
    
    def on_mouseenter(_ev=None):
        if isinstance(target_generator := _get_route_generator(target_path), LazyComponentGenerator):
            target_generator._preload()

    return html.A(
        {"@click": navigate, "@mouseenter": on_mouseenter},
        context.slots("default"),
    )
```

The `_preload()` method on `LazyComponentGenerator` triggers `_resolve()` without rendering — just importing the module and registering the component. This makes the actual navigation near-instant since the module is already loaded.

### Part 3: Component Shell (Loading Placeholder)

When a lazy route is first navigated to and the module import takes noticeable time (rare for pure-Python imports within an already-loaded wheel, but possible for complex modules), the RouterView should show a loading placeholder.

#### Shell Rendering Strategy

When `LazyComponentGenerator.__call__()` is invoked:

1. **If already resolved**: Render normally (no shell needed)
2. **If not yet resolved**:
   - Show the shell component (a configurable placeholder, default: a simple `<div>` with `webcompy-loading` styling)
   - Schedule the import via `setTimeout(0)` to avoid blocking the main thread
   - Once resolved, replace the shell with the real component

However, since Python `import` within Pyodide is synchronous and fast for already-loaded wheel contents, the shell rendering is primarily useful for:

- Complex modules with heavy initialization (e.g., matplotlib rendering setup)
- Future compatibility with async module loading
- Providing a visual placeholder for slow network conditions if wheel splitting enables per-route wheel downloads

#### Shell API

```python
class LazyComponentGenerator(ComponentGenerator):
    def __init__(
        self,
        import_path: str,
        caller_file: str,
        shell: ComponentGenerator | None = None,
    ) -> None:
        ...
        self._shell = shell
```

Usage:

```python
def LoadingShell(context):
    return html.DIV({"class": "route-loading"}, "Loading...")

router = Router(
    {"path": "/demo", "component": lazy(
        "pages.demo:DemoPage",
        __file__,
        shell=LoadingShell,
    )},
)
```

When the shell is not provided, the lazy component renders synchronously on first navigation (import + render in one step). When a shell is provided, the lazy component shows the shell first and swaps to the real component after import.

#### Shell Integration with SwitchElement

The `SwitchElement` that `RouterView` uses needs to handle `LazyComponentGenerator` specially:

```python
# In Router._get_elements_generator():
def _get_elements_generator(self, args):
    ...
    if match:
        component = args[3]  # RouteType[3] = ComponentGenerator
        if isinstance(component, LazyComponentGenerator) and component._shell and not component._resolved:
            return (match, lambda: component._shell(None))
        else:
            return (match, lambda: component(props))
    ...
```

After the lazy component resolves, a signal change triggers `SwitchElement._refresh()`, which then renders the real component instead of the shell.

### Part 4: SSG Compatibility

For static site generation, all lazy routes must be eagerly resolved so that `AppDocumentRoot._render_html()` can produce the correct HTML output. This requires:

1. During SSG, `LazyComponentGenerator._resolve()` is called for the current route before rendering
2. The `Router.__set_path__()` method triggers resolution via the existing `SwitchElement._refresh()` path

Since SSG already sets the path and renders, this should work naturally — `LazyComponentGenerator.__call__()` will call `_resolve()` when the component is instantiated during SSG rendering.

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
    {"path": "/docs", "component": lazy("pages.docs:DocsPage", __file__)},
    {"path": "/demo", "component": lazy("pages.demo:DemoPage", __file__, shell=LoadingShell)},
)
```

Recommended pattern: Keep the initial/home route eager (it's needed at startup anyway) and make all other routes lazy.

## Specs Affected

- `router` — adds `lazy()` function; updates `RouterPage` type to accept `LazyComponentGenerator`; adds route preloading via `RouterLink` hover; adds shell placeholder support
- `components` — no changes needed (`LazyComponentGenerator` is a `ComponentGenerator` subclass, compatible with existing APIs)
- `wheel-builder` — no changes needed
- `cli` — no changes needed
- `app` — no changes needed