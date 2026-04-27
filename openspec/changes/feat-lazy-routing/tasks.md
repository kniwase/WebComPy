# Tasks: Lazy Routing — Deferred Module Import and Route Preloading

- [ ] **Task 0: Rename ComponentGenerator private attributes**

**Estimated time: ~0.5 hours**

### Steps

1. Open `webcompy/components/_generator.py`.
2. Rename `ComponentGenerator` name-mangled attributes to single-underscore:
   - `__name` → `_name`
   - `__id` → `_id`
   - `__style` → `_style`
   - `__registered` → `_registered`
   - `__component_def` → `_component_def`
3. Rename `ComponentStore.__components` → `ComponentStore._components`.
4. Update all references within the same file to use the new names.
5. Verify no external code references the mangled forms (they don't per codebase audit).
6. Run tests to confirm no behavioral change.

### Acceptance Criteria

- All references to `__name`, `__id`, `__style`, `__registered`, `__component_def` in `ComponentGenerator` and `__components` in `ComponentStore` are updated to single-underscore forms.
- All existing tests pass.
- No public API change — `scoped_style`, `__call__`, `_try_register`, `define_component` all continue to work.

---

- [ ] **Task 1: Implement `LazyComponentGenerator` class and `lazy()` function**

**Estimated time: ~2.5 hours**

### Steps

1. Create `webcompy/router/_lazy.py`.
2. Implement `LazyComponentGenerator(ComponentGenerator)`:
   - `__init__(import_path, caller_file)` — parse `import_path`, initialize minimal ComponentGenerator fields without calling `super().__init__()`.
   - `_resolve()` — `importlib.import_module(module_path)`, `getattr(module, attr_name)`, validate `isinstance(resolved, ComponentGenerator)`, copy attributes from resolved to self, call `resolved._try_register()`.
   - `_preload()` — call `_resolve()` without rendering.
   - `__call__(props, slots=None)` — resolve and delegate to `resolved(props, slots=slots)`.
   - `__getattr__(name)` — delegate to resolved.
   - `scoped_style` property getter/setter — delegate to resolved.
3. Implement `lazy(import_path, caller_file) -> ComponentGenerator`:
   - Validate `import_path` format (must contain `:`, non-empty module and attribute).
   - Validate `caller_file` is non-empty.
   - Return `LazyComponentGenerator(import_path, caller_file)`.
4. Add `LazyComponentGenerator` and `lazy` to `webcompy/router/__init__.py` exports and `__all__`.
5. Add `WebComPyRouterException` import (already exists in `_pages.py`).

### Acceptance Criteria

- `LazyComponentGenerator` is importable from `webcompy.router`.
- `lazy("myapp.pages.docs:DocsPage", __file__)` returns a `ComponentGenerator` subclass.
- `isinstance(LazyComponentGenerator(...), ComponentGenerator)` is True.
- `__call__()` resolves the module on first use and caches the result.
- `_preload()` resolves without rendering.
- Invalid `import_path` format raises `WebComPyRouterException` at call time.
- Non-`ComponentGenerator` attribute raises `WebComPyRouterException` at resolve time.

---

- [ ] **Task 2: Add auto-preload to Router and RouterView**

**Estimated time: ~1 hour**

### Steps

1. Open `webcompy/router/_router.py`.
2. Add `preload: bool = True` parameter to `Router.__init__()`.
3. Implement `Router.preload_lazy_routes()` method:
   - Iterate over `self.__routes__`, check each `route[3]` for `LazyComponentGenerator` with `_resolved is None`.
   - In browser: `browser.window.setTimeout(component._preload, 0)`.
   - In non-browser: call `component._preload()` immediately.
4. Add `Router._get_component_for_path(path)` method:
   - Iterate over `self.__routes__`, match path against each route's regex matcher.
   - Return the matched `ComponentGenerator` or `None`.
5. Open `webcompy/router/_view.py`.
6. In `RouterView._on_set_parent()` (or add it if not present), call `self._router.preload_lazy_routes()` after initial render setup.
7. Ensure `preload=False` skips the auto-preload.

### Acceptance Criteria

- `Router(preload=True)` (default) auto-preloads all lazy routes after initial render.
- `Router(preload=False)` skips auto-preload.
- `Router.preload_lazy_routes()` resolves unresolved `LazyComponentGenerator` instances.
- In browser, preloading uses `setTimeout(0)`.
- In SSG, preloading happens immediately.
- `Router._get_component_for_path()` returns the correct `ComponentGenerator` for a matched path.

---

- [ ] **Task 3: Add RouterLink hover preloading**

**Estimated time: ~1 hour**

### Steps

1. Open `webcompy/router/_link.py`.
2. Add `_on_mouseenter` method to `TypedRouterLink`:
   - Get target path from `self._to`.
   - Call `self._router._get_component_for_path(target_path)`.
   - If result is `LazyComponentGenerator`, call `_preload()`.
3. Add `"@mouseenter": self._on_mouseenter` to `_generate_attrs()`.
4. Handle edge cases:
   - Path with query params: strip query before matching.
   - Path with hash: strip hash before matching.
   - Path with base_url: handle base_url stripping.

### Acceptance Criteria

- Hovering over a `RouterLink` to a lazy route triggers `_preload()`.
- Hovering over a `RouterLink` to an eager route does nothing extra.
- Clicking the link shortly after hover results in instant navigation.
- Preloading does not affect eager routes.

---

- [ ] **Task 4: Add unit tests for lazy routing**

**Estimated time: ~1.5 hours**

### Steps

1. Create `tests/test_lazy_routing.py`:
   - `test_lazy_is_component_generator`: Assert `isinstance(lazy(...), ComponentGenerator)`.
   - `test_lazy_invalid_import_path_format`: Assert `WebComPyRouterException` for missing `:`.
   - `test_lazy_empty_module_path`: Assert `WebComPyRouterException` for `":DocsPage"`.
   - `test_lazy_empty_attribute_name`: Assert `WebComPyRouterException` for `"myapp.pages:"`.
   - `test_lazy_empty_caller_file`: Assert `WebComPyRouterException` for `caller_file=""`.
   - `test_lazy_resolve_imports_module`: Create a temporary module with a `ComponentGenerator`, use `lazy()` to create `LazyComponentGenerator`, call `_resolve()`, assert the returned component is correct.
   - `test_lazy_resolve_non_component_generator`: Use `lazy()` with a module attribute that is not a `ComponentGenerator`, assert `WebComPyRouterException`.
   - `test_lazy_call_delegates_to_resolved`: Call `LazyComponentGenerator.__call__(props)` and verify it creates a `Component` from the resolved generator.
   - `test_lazy_preload_resolves_without_rendering`: Call `_preload()` and verify module is imported but no rendering occurs.
   - `test_lazy_scoped_style_delegates`: Set `scoped_style` on resolved generator, verify `LazyComponentGenerator.scoped_style` delegates correctly.
   - `test_router_preload_lazy_routes`: Create `Router` with both eager and lazy routes, call `preload_lazy_routes()`, verify all lazy routes are resolved.
   - `test_router_get_component_for_path`: Verify `_get_component_for_path()` returns the correct `ComponentGenerator` for matched paths and `None` for unmatched paths.

### Acceptance Criteria

- All tests pass.
- Tests cover: lazy creation, validation, resolution, delegation, preloading, Router integration.

---

- [ ] **Task 5: Convert docs_src routes to use lazy routing**

**Estimated time: ~1 hour**

### Steps

1. Open `docs_src/router.py`.
2. Keep `HomePage` as an eager import (initial page).
3. Convert all other route components to use `lazy()`:
   ```python
   from webcompy.router import Router, lazy
   
   router = Router(
       {"path": "/", "component": HomePage},
       {"path": "/documents", "component": lazy("docs_src.pages.document:DocumentHomePage", __file__)},
       {"path": "/sample/helloworld", "component": lazy("docs_src.pages.demo.helloworld:HelloWorldPage", __file__)},
       ...
       default=NotFound,
       mode="history",
       base_url="",
   )
   ```
4. Start dev server and verify:
   - Home page loads correctly.
   - No errors on initial load.
   - Navigation to other pages triggers module import and renders correctly.
   - Auto-preload resolves remaining lazy routes after initial render.
5. Run existing E2E tests to verify no regressions.

### Acceptance Criteria

- `docs_src` app works with lazy routing.
- Navigation to lazy routes works correctly.
- No console errors.
- Existing E2E tests pass.

---

- [ ] **Task 6: Add SSG compatibility validation**

**Estimated time: ~0.5 hours**

### Steps

1. Run `python -m webcompy generate --app docs_src.bootstrap:app` with lazy routes.
2. Verify all routes produce correct HTML (no missing content).
3. Ensure `LazyComponentGenerator._resolve()` is called during SSG rendering.
4. Verify `preload_lazy_routes()` resolves immediately in non-browser environments.

### Acceptance Criteria

- SSG output is correct for lazy routes.
- No blank pages or missing components.

---

## Dependencies

- None. Independent of hydration work.

## Specs to Update

- `openspec/specs/router/spec.md` — add `lazy()` function, `LazyComponentGenerator`, auto-preload, `RouterLink` hover preloading, `Router.preload` parameter, `ComponentGenerator` attribute rename
- `openspec/specs/components/spec.md` — add `ComponentGenerator` attribute rename requirement