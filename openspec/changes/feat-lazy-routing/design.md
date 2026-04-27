# Design: Lazy Routing — Deferred Module Import and Route Preloading

## Design Decisions

### D1: `lazy()` creates a deferred `ComponentGenerator` wrapper
The `lazy()` function returns a `LazyComponentGenerator` that defers `importlib.import_module()` until first use. This wrapper is a subclass of `ComponentGenerator` so the existing `Router` works without modification — `RouteType[3]` accepts `ComponentGenerator[RouterContext]`, and `LazyComponentGenerator` satisfies this type.

### D2: Absolute module paths only
`lazy()` requires an **absolute** dotted module path (e.g., `"myapp.pages.docs:DocsPage"`). Relative paths like `".pages.docs:DocsPage"` are not supported. This avoids fragile `__file__`-to-package-name derivation that would break across Pyodide (virtual filesystem), SSG (arbitrary paths), and development environments (different working directories). The `caller_file` parameter is used for validation and error messages only.

### D3: ComponentGenerator attributes must be renamed for subclass access
`ComponentGenerator` uses name-mangled private attributes (`__name`, `__id`, `__style`, `__registered`, `__component_def`). The double-underscore prefix prevents `LazyComponentGenerator` from accessing these attributes because Python name-mangles them to `_ComponentGenerator__name`, etc. Before implementing `LazyComponentGenerator`, all name-mangled attributes in `ComponentGenerator` must be renamed to single-underscore variants (`_name`, `_id`, `_style`, `_registered`, `_component_def`). Similarly, `ComponentStore.__components` becomes `ComponentStore._components`. No external code accesses these via the mangled form, so this is a safe refactor.

### D4: LazyComponentGenerator skips `super().__init__()`
`ComponentGenerator.__init__()` requires a `component_def` function and immediately calls `_try_register()`. Since `LazyComponentGenerator` doesn't have a component definition yet (it will be resolved lazily), it cannot call `super().__init__()`. Instead, it manually initializes the minimal fields (`_name`, `_id`, `_style`, `_registered = False`, `_component_def = None`) and defers registration until `_resolve()` is called.

### D5: After resolution, attributes delegate to the resolved generator
When `_resolve()` succeeds, `LazyComponentGenerator` copies all internal attributes from the resolved `ComponentGenerator`:
```python
self._component_def = resolved._component_def
self._name = resolved._name
self._id = resolved._id
self._style = resolved._style
self._registered = resolved._registered
```
This ensures that `scoped_style`, `_try_register()`, and `ComponentStore` iteration (which accesses `component.scoped_style`) all work correctly after resolution.

### D6: Auto-preload after initial render (not Shell)
Python `import` in Pyodide is synchronous — calling `_resolve()` blocks until the import completes. There is no viable window between navigation and render where a "shell" (loading placeholder) could be displayed. Instead, `Router.preload_lazy_routes()` imports all remaining lazy routes after the initial page renders, using `setTimeout(0)` in the browser to avoid blocking the render. This approach:
- Preserves the startup performance benefit (only the initial route is imported at startup)
- Eliminates user-facing latency for subsequent navigation (all routes are preloaded)
- Requires no signal-system integration (no shell-swap mechanism needed)

### D7: RouterLink hover preloading complements auto-preload
Auto-preload starts after the initial render via `setTimeout(0)`. If a user hovers over a `RouterLink` before auto-preload reaches that route, `mouseenter` triggers immediate `_preload()` on just that route. This provides the best of both: fast initial render + instant navigation.

### D8: SSG eagerly resolves lazy routes
In non-browser environments, `Router.preload_lazy_routes()` calls `_preload()` immediately (no `setTimeout`). Combined with `LazyComponentGenerator.__call__()` calling `_resolve()` on navigation, this ensures all lazy routes are fully resolved during SSG rendering.

### D9: RouterView refactored from Element to DynamicElement
Currently, `RouterView` extends `Element` and renders as a `<div webcompy-routerview>` wrapper around `SwitchElement`. This is conceptually incorrect — `RouterView`'s purpose is to manage dynamic children (the matched route component), which is exactly the `DynamicElement` pattern. The wrapper `<div>` serves no purpose:

- The `webcompy-routerview` attribute is never referenced by CSS, JavaScript, or test code.
- `SwitchElement` (the only child) is already a `DynamicElement` that manages its own DOM operations.
- `RouterView` adds no DOM behavior beyond delegating to `SwitchElement`.

Refactoring to `DynamicElement` provides:

1. **Conceptual alignment**: `RouterView` manages dynamic children — that is what `DynamicElement` is for. Follows the same pattern as `SwitchElement` and `RepeatElement`.
2. **`_on_set_parent()` lifecycle**: The natural hook for scheduling auto-preload after children are initialized, replacing the workaround of scheduling from `__init__`.
3. **DOM simplification**: Removes one unnecessary wrapper `<div>` per page.

The `DynamicElement` subclass contract:
- No `_tag_name`, no `_attrs`, no `_event_handlers` — no DOM node ownership.
- `_on_set_parent()` implementation initializes `_children` and schedules preload.
- `_render_html()` concatenates children's HTML without a wrapper tag.
- `_is_patchable` returns `False` for `DynamicElement` ↔ any — not a concern since `RouterView` has exactly one child (`SwitchElement`) that is never patched in place.
- DOM positioning: `_position_element_nodes()` skips `DynamicElement` and positions its children directly in the parent node.

**SSG output change**: `<div webcompy-routerview>...content...</div>` → `...content...`. Safe because `webcompy-routerview` is unused.

### D10: RouterLink mouseenter goes through events dict, not attrs
WebComPy's `Element` class separates `attrs` (DOM attribute strings set via `setAttribute`) from `events` (event handlers registered via `addEventListener`). The `mouseenter` handler MUST go through the `events` dict (the `addEventListener` path), NOT through `attrs`. Setting `@mouseenter` as an attribute string would not work — DOM event handlers require `addEventListener`, not inline attributes.

## Architecture

### Lazy Component Resolution Flow

```
Startup (no lazy import):
═════════════════════════
  router = Router(
      {"path": "/docs", "component": lazy("myapp.pages.docs:DocsPage", __file__)},
  )
  → LazyComponentGenerator created (lightweight)
  → No import

First navigation to /docs:
═════════════════════════════
  Router.match("/docs")
  → Returns LazyComponentGenerator
  → SwitchElement selects it
  → LazyComponentGenerator.__call__(props)
     → _resolve()
        → importlib.import_module("myapp.pages.docs")
        → getattr(module, "DocsPage")
        → DocsPage._try_register() in ComponentStore
        → _resolved ← DocsPage
        → Copy attributes from resolved to self
     → _resolved(props)  (renders component)
  → DOM updated

Auto-preload after initial render:
═════════════════════════════════
  RouterView._on_set_parent()
  → Initialize _children with SwitchElement
  → Schedule preload (setTimeout in browser, immediate in SSG)
  → self._router.preload_lazy_routes()
  → For each unresolved LazyComponentGenerator:
     Browser: browser.window.setTimeout(component._preload(), 0)
     SSG: component._preload()  (immediate)

RouterLink hover preloading:
════════════════════════════════
  mouseenter event (via addEventListener)
  → router._get_component_for_path("/docs")
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

    def __init__(self, import_path: str, caller_file: str) -> None:
        self._import_path = import_path
        self._caller_file = caller_file
        self._resolved = None
        attr_name = import_path.rsplit(":", 1)[-1]
        self._name = attr_name
        self._id = generate_id(attr_name)
        self._style = {}
        self._component_def = None
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

### `RouterView` as DynamicElement

```python
class RouterView(DynamicElement):
    def __init__(self) -> None:
        try:
            router = inject(_ROUTER_KEY)
        except InjectionError:
            raise RuntimeError("'Router' instance is not provided via DI.") from None
        self._router = router
        self._switch = SwitchElement(router.__cases__, router.__default__)
        super().__init__()

    def _on_set_parent(self):
        self._children = [self._switch]
        self._switch._parent = self

        if not browser:
            # SSG: resolve SwitchElement and preload immediately
            self._switch._on_set_parent()
            if self._router._preload:
                self._router.preload_lazy_routes()
        else:
            # Browser: schedule preload after initial render
            if self._router._preload:
                def _schedule_preload():
                    self._router.preload_lazy_routes()
                browser.window.setTimeout(_schedule_preload, 0)
```

### Auto-Preload Integration

```python
class Router:
    def __init__(self, *pages, default=None, mode="hash", base_url="", preload=True):
        ...
        self._preload = preload

    def preload_lazy_routes(self) -> None:
        """Preload all unresolved lazy routes after initial render."""
        from webcompy._browser._modules import browser
        for route in self.__routes__:
            component = route[3]
            if isinstance(component, LazyComponentGenerator) and component._resolved is None:
                if browser:
                    def _do_preload(c=component):
                        c._preload()
                    browser.window.setTimeout(_do_preload, 0)
                else:
                    component._preload()
```

### RouterLink Preloading

```python
class TypedRouterLink(Element):
    def __init__(self, *, to, text, ...):
        ...
        super().__init__(
            "a",
            attrs=self._generate_attrs(),
            events={"click": self._on_click, "mouseenter": self._on_mouseenter},
            children=self._generate_children(),
        )

    def _on_mouseenter(self, _ev=None):
        to_path = self._to.value if isinstance(self._to, SignalBase) else self._to
        target = self._router._get_component_for_path(to_path)
        if isinstance(target, LazyComponentGenerator):
            target._preload()

    def _refresh(self, *_: Any):
        self._attrs = self._generate_attrs()
        self._event_handlers = {"click": self._on_click, "mouseenter": self._on_mouseenter}
        self._init_children(self._generate_children())
        self._render()
```

Note: `mouseleave` is not needed — there is no visual change to the link on hover, and preloading is harmless even if the user moves away.

### Router._get_component_for_path

```python
class Router:
    def _get_component_for_path(self, path: str) -> ComponentGenerator | None:
        """Return the ComponentGenerator for the given path, or None if no match."""
        clean_path = path.strip("/")
        for route in self.__routes__:
            _, matcher, _, component, _ = route
            if matcher(clean_path):
                return component
        return None
```

## Risk: `importlib` in Pyodide

Pyodide uses Emscripten's virtual filesystem where `importlib.import_module()` works identically to CPython for modules that are already in the wheel (installed by micropip). Since WebComPy's wheel builder includes all `.py` files from the app package (filesystem-based discovery, not import-graph-based), `importlib.import_module("myapp.pages.docs")` will succeed as long as `myapp/pages/docs.py` exists in the wheel.

The `caller_file` parameter is used for validation only — the absolute module path in `import_path` is used directly with `importlib.import_module()`, which resolves it against `sys.path`.

## Risk: RouterView DOM structure change

Refactoring `RouterView` from `Element` to `DynamicElement` removes the wrapper `<div webcompy-routerview>` from the DOM. This could affect:

1. **User CSS** targeting `[webcompy-routerview]` or `.routerview` selectors — Codebase search found zero references to this attribute outside its definition.
2. **E2E tests** targeting the router view div — Existing E2E tests use `webcompy-app` or component-specific selectors, not the router view div.
3. **SSG output** — The generated HTML will have one fewer wrapper div. This is a cosmetic change that does not affect content.

All identified risks are minimal. The `webcompy-routerview` attribute has no consumers.

## Rollback Path

If lazy routing introduces import resolution issues:
1. Keep eager imports for all routes (migration path: replace `lazy(...)` with direct `from x import y`).
2. `LazyComponentGenerator` remains usable, but routes can be made eager at user discretion.

If the RouterView refactor causes issues:
1. Revert `RouterView` to `Element` and move preload scheduling back to `__init__` with `setTimeout(0)`.
2. The lazy routing functionality does not depend on `RouterView` being `DynamicElement` — it is a separate improvement.

## Performance Impact

For `docs_src` (6+ page modules):
- **Before:** All 6+ modules imported at startup.
- **After (with lazy):** Only the home module imported at startup; others deferred. On a single-page visit, startup import time is reduced by ~80% (5/6 of modules deferred). Auto-preload imports remaining modules after the initial render, so subsequent navigation is instant.

DOM reduction: one fewer `<div>` wrapper per page render (RouterView refactor).

## Dependencies

- **Informed by:** `feat/hydration-measurement` — profiling data shows time saved.
- **Informs:** `feat/hydration-full` — lazy routes reduce the number of components to hydrate.

## Refactor Required Before Implementation

### ComponentGenerator Attribute Rename

`ComponentGenerator` uses name-mangled attributes that prevent `LazyComponentGenerator` from accessing them via inheritance. These must be renamed to single-underscore variants:

| File | Old Name | New Name |
|---|---|---|
| `webcompy/components/_generator.py` | `ComponentGenerator.__name` | `ComponentGenerator._name` |
| `webcompy/components/_generator.py` | `ComponentGenerator.__id` | `ComponentGenerator._id` |
| `webcompy/components/_generator.py` | `ComponentGenerator.__style` | `ComponentGenerator._style` |
| `webcompy/components/_generator.py` | `ComponentGenerator.__registered` | `ComponentGenerator._registered` |
| `webcompy/components/_generator.py` | `ComponentGenerator.__component_def` | `ComponentGenerator._component_def` |
| `webcompy/components/_generator.py` | `ComponentStore.__components` | `ComponentStore._components` |

No external code accesses these via the mangled form. This is a safe, behavior-preserving refactor.

## Specs to Update

- `openspec/specs/router/spec.md` — add `lazy()` function, `LazyComponentGenerator`, `RouterView` as `DynamicElement`, auto-preload, `RouterLink` hover preloading, `Router.preload` parameter
- `openspec/specs/components/spec.md` — no changes needed (`LazyComponentGenerator` is a `ComponentGenerator` subclass)