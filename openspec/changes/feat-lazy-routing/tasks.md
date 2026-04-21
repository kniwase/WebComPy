# Tasks: Lazy Routing — Deferred Module Import and Route Preloading

## Task 1: Implement `LazyComponentGenerator` class

**Estimated time: ~1 hour**

### Steps

1. Create or open `webcompy/router/lazy.py`.
2. Implement `LazyComponentGenerator` with:
   - `__init__(import_path, caller_file, shell=None)`
   - `_resolve()` with `importlib.import_module` and absolute package resolution from `caller_file`
   - `__call__(props, slots=None)` delegate
   - `__getattr__(name)` delegate
   - `scoped_style` property delegate
   - `_preload()` method
3. Export `lazy()` function that returns `LazyComponentGenerator(...)`.
4. Add `LazyComponentGenerator` and `lazy` to `webcompy/router/__init__.py`.

### Acceptance Criteria

- `LazyComponentGenerator` is importable from `webcompy.router`.
- `lazy("module.path:Component", __file__)` returns a `ComponentGenerator` subclass.
- `__call__()` resolves the module on first use and caches the result.
- `_preload()` resolves without rendering.

---

## Task 2: Integrate shell rendering into Router and RouterView

**Estimated time: ~0.5 hours**

### Steps

1. Open the module containing `Router._get_elements_generator()`.
2. Modify to check for `LazyComponentGenerator` and return shell if applicable:
   ```python
   if isinstance(component, LazyComponentGenerator):
       if component._shell and not component._resolved:
           return (match, lambda: component._shell(None))
   ```
3. Ensure `SwitchElement` handles the shell component correctly (it should render the shell as a normal component).
4. After lazy component resolves, `SwitchElement._refresh()` naturally re-renders with the real component.

### Acceptance Criteria

- When `LazyComponentGenerator._shell` is set and `_resolved` is None, RouterView renders the shell.
- After `_resolve()`, the real component replaces the shell.
- When no shell is set, lazy component renders synchronously.

---

## Task 3: Add RouterLink hover preloading

**Estimated time: ~0.5 hours**

### Steps

1. Open the module containing `RouterLink` component definition.
2. Add `@mouseenter` event handler:
   ```python
   def on_mouseenter(_ev=None):
       target = _get_route_generator(target_path)
       if isinstance(target, LazyComponentGenerator):
           target._preload()
   ```
3. Pass `on_mouseenter` to `html.A({"@mouseenter": on_mouseenter, ...})`.
4. Ensure `_get_route_generator()` is accessible from `RouterLink` context (may need to import a utility function).

### Acceptance Criteria

- Hovering over a `RouterLink` to a lazy route triggers `_preload()`.
- Clicking the link shortly after hover results in instant navigation.
- Hovering over eager routes does nothing extra.

---

## Task 4: Add unit tests for lazy routing

**Estimated time: ~1 hour**

### Steps

1. Create `tests/unit/test_lazy_routing.py`:
   - `test_lazy_component_generator_is_component_generator`: Assert `isinstance(LazyComponentGenerator(...), ComponentGenerator)`.
   - `test_lazy_resolve_imports_module`: Create a temporary module with a `ComponentGenerator`, use `lazy()` with `__file__` set to a temp file in the same directory, call `_resolve()`, assert the returned component is the one from the module.
   - `test_shell_renders_before_resolve`: Create `LazyComponentGenerator(shell=ShellComp)`, assert `__call__()` returns a shell component instance when not yet resolved.
   - `test_shell_replaced_after_resolve`: Resolve the lazy component, mock trigger a signal change on SwitchElement, assert the real component replaces the shell.
   - `test_router_link_preload_on_hover`: Mock `_get_route_generator` to return a `LazyComponentGenerator`, simulate hover, assert `_preload()` was called.

### Acceptance Criteria

- All tests pass.
- Tests cover module resolution, shell rendering, and preloading.

---

## Task 5: Add integration test and validate docs_src app

**Estimated time: ~1 hour**

### Steps

1. Convert `docs_src` routes to use `lazy()` for non-home pages:
   ```python
   from webcompy.router import lazy
   router = Router(
       {"path": "/", "component": HomePage},
       {"path": "/docs", "component": lazy("docs_src.pages.docs:DocsPage", __file__)},
       ...
   )
   ```
2. Start dev server and verify:
   - Home page loads correctly.
   - No errors on initial load.
   - Navigation to `/docs` triggers module import and renders correctly.
3. Run Playwright MCP e2e test against the lazy-routed app.
4. Verify profiling data shows reduced `imports_done → init_done` time.

### Acceptance Criteria

- `docs_src` app works with lazy routing.
- Navigation works correctly.
- Profiling shows measurable improvement.
- No console errors.

---

## Task 6: Update SSG compatibility tests

**Estimated time: ~0.5 hours**

### Steps

1. Run `python -m webcompy generate` on `docs_src` with lazy routes.
2. Verify all routes produce correct HTML (no missing content).
3. Ensure `LazyComponentGenerator._resolve()` is called during SSG rendering.

### Acceptance Criteria

- SSG output is correct for lazy routes.
- No blank pages or missing components.

---

## Dependencies

- None. Independent of hydration work.

## Specs to Update

- `openspec/specs/router/spec.md` — add `lazy()` function to route definitions.
- `openspec/specs/router/spec.md` — add RouterLink preloading requirement.
- `openspec/specs/router/spec.md` — add shell placeholder requirement.
