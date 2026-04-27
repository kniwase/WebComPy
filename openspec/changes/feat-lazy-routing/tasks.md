# Tasks: Lazy Routing — Deferred Module Import and Route Preloading

- [x] **Task 0: Rename ComponentGenerator private attributes**

**Estimated time: ~0.5 hours**

### Context

`ComponentGenerator` uses name-mangled attributes (`__name`, `__id`, `__style`, `__registered`, `__component_def`). Python name-mangles these to `_ComponentGenerator__name`, etc., which prevents subclasses (including `LazyComponentGenerator`) from accessing them. No external code references the mangled forms — all external access is through the public interfaces (`scoped_style` property, `__call__`, `_try_register`). `ComponentStore.__components` similarly needs renaming.

### Steps

1. Open `webcompy/components/_generator.py`.
2. Rename `ComponentGenerator` class-level annotations and all `self.__` references:
   - `__name` → `_name` (lines 52, 64, 78)
   - `__id` → `_id` (lines 53, 65, 101)
   - `__style` → `_style` (lines 54, 62, 93, 102)
   - `__registered` → `_registered` (lines 55, 66, 71, 79)
   - `__component_def` → `_component_def` (lines 63, 89)
3. Rename `ComponentStore.__components` → `_components` (lines 29, 31, 35, 40).
4. Run `uv run ruff check . && uv run ruff format . && uv run pyright && uv run python -m pytest tests/ --tb=short`.
5. Verify no behavioral change — the rename is purely internal.

### Acceptance Criteria

- All name-mangled attributes in `ComponentGenerator` and `ComponentStore` are single-underscore.
- All existing tests pass.
- No public API change — `scoped_style`, `__call__`, `_try_register`, `define_component` all continue to work.

### Key File Paths

- `webcompy/components/_generator.py` — the only file that needs changes
- `webcompy/app/_root_component.py:186` — reads `component.scoped_style` (public property, unaffected)
- `webcompy/components/_component.py:144` — recomputes ID independently via `generate_id()` (unaffected)

---

- [x] **Task 1: Implement `LazyComponentGenerator` class and `lazy()` function**

**Estimated time: ~2.5 hours**

### Context

`ComponentGenerator.__init__(name, component_def)` requires a component definition function and immediately calls `_try_register()`. Since `LazyComponentGenerator` doesn't have a component definition yet, it must NOT call `super().__init__()`. Instead, it initializes minimal fields manually and defers registration until `_resolve()`.

After resolution, all internal attributes (`_name`, `_id`, `_style`, `_registered`, `_component_def`) are copied from the resolved generator so that `scoped_style`, `_try_register()`, and `ComponentStore` iteration work correctly.

`lazy()` requires an **absolute** dotted module path (e.g., `"myapp.pages.docs:DocsPage"`). Relative paths are not supported because `__file__`-to-package derivation is fragile across Pyodide/SSG/dev environments.

### Steps

1. Create `webcompy/router/_lazy.py` with import of `importlib`, `ComponentGenerator`, `generate_id`, `WebComPyRouterException`.
2. Implement `LazyComponentGenerator(ComponentGenerator)`:
   - `__init__(self, import_path: str, caller_file: str)`:
     - Parse `import_path` via `rsplit(":", 1)` to get module path and attribute name.
     - Initialize minimal `ComponentGenerator` fields WITHOUT calling `super().__init__()`:
       - `self._name = attr_name` (use the attribute name as display name)
       - `self._id = generate_id(attr_name)`
       - `self._style = {}`
       - `self._component_def = None`
       - `self._registered = False`
     - Store `self._import_path = import_path`, `self._caller_file = caller_file`, `self._resolved = None`.
   - `_resolve(self) -> ComponentGenerator`:
     - If `self._resolved is None`:
       - `module_path, attr_name = self._import_path.rsplit(":", 1)`
       - `module = importlib.import_module(module_path)` (absolute path, no `package` argument)
       - `resolved = getattr(module, attr_name)`
       - Validate `isinstance(resolved, ComponentGenerator)`, raise `WebComPyRouterException` if not.
       - Copy attributes: `self._component_def = resolved._component_def`, `self._name = resolved._name`, `self._id = resolved._id`, `self._style = resolved._style`, `self._registered = resolved._registered`.
       - Call `resolved._try_register()`.
       - Set `self._resolved = resolved`.
     - Return `self._resolved`.
   - `_preload(self) -> None`: Call `self._resolve()`.
   - `__call__(self, props, *, slots=None)`: `resolved = self._resolve()` then `return resolved(props, slots=slots)`.
   - `__getattr__(self, name: str)`: `return getattr(self._resolve(), name)`.
   - `scoped_style` property getter: `return self._resolve().scoped_style`.
   - `scoped_style` property setter: `self._resolve().scoped_style = value`.
3. Implement `lazy(import_path: str, caller_file: str) -> ComponentGenerator`:
   - Validate format: `import_path` must contain `:`, non-empty module path, non-empty attribute name.
   - Validate `caller_file` is non-empty.
   - Return `LazyComponentGenerator(import_path, caller_file)`.
4. Update `webcompy/router/__init__.py`:
   - Import `LazyComponentGenerator` and `lazy` from `webcompy.router._lazy`.
   - Add `"LazyComponentGenerator"` and `"lazy"` to `__all__`.
5. Run lint, typecheck, and tests.

### Acceptance Criteria

- `LazyComponentGenerator` is importable from `webcompy.router`.
- `lazy("myapp.pages.docs:DocsPage", __file__)` returns a `ComponentGenerator` subclass.
- `isinstance(LazyComponentGenerator(...), ComponentGenerator)` is True.
- `__call__()` resolves the module on first use and caches the result.
- `_preload()` resolves without rendering.
- Invalid `import_path` format raises `WebComPyRouterException` at `lazy()` call time.
- Non-`ComponentGenerator` attribute raises `WebComPyRouterException` at `_resolve()` time.
- `scoped_style` getter delegates to the resolved `ComponentGenerator`.
- `scoped_style` setter delegates to the resolved `ComponentGenerator`.

### Key File Paths

- `webcompy/router/_lazy.py` — new file
- `webcompy/router/__init__.py` — add exports
- `webcompy/router/_pages.py:7` — `WebComPyRouterException` (import from here)
- `webcompy/components/_libs.py:160` — `generate_id()` (import from here)
- `webcompy/components/_generator.py` — `ComponentGenerator` (import from here)

### Important Notes

- Do NOT call `super().__init__()` — it requires a `component_def` function that doesn't exist yet.
- `_resolve()` uses `importlib.import_module(module_path)` with no `package` argument because the `import_path` is an absolute dotted path.
- After resolution, attribute copying ensures `AppDocumentRoot.style` (which iterates `store.components.values()` accessing `scoped_style`) works correctly even for lazy components.

---

- [x] **Task 2: Refactor RouterView to DynamicElement and add auto-preload**

**Estimated time: ~1.5 hours**

### Context

`RouterView` currently extends `Element` and renders as `<div webcompy-routerview>` wrapping a `SwitchElement`. This wrapper div is conceptually wrong — `RouterView` manages dynamic children, which is what `DynamicElement` does. The `webcompy-routerview` attribute is not referenced anywhere in CSS, JS, or tests.

By making `RouterView` a `DynamicElement`, it gets `_on_set_parent()` which is the natural lifecycle hook for:
1. Initializing children (the `SwitchElement`)
2. Scheduling auto-preload of lazy routes

`DynamicElement` contract:
- No `_tag_name`, no `_attrs`, no `_event_handlers` — no DOM node ownership.
- `_on_set_parent()` initializes `_children` and schedules preload.
- `_render_html()` concatenates children's HTML without a wrapper tag.
- `_position_element_nodes()` skips `DynamicElement` and positions its children directly in the parent node.
- `_is_patchable` returns `False` for `DynamicElement` — not a concern since `RouterView` has exactly one child.

`DynamicElement._parent` setter (in `_dynamic.py:47-49`) calls `self._on_set_parent()`. This is called when the parent component adds `RouterView` to its children, which happens during component initialization.

SSG pipeline: `app.set_path(path)` → signal propagation → `SwitchElement._refresh()` → `LazyComponentGenerator.__call__()` → `_resolve()`. Then `preload_lazy_routes()` resolves remaining routes immediately. Then `generate_html()` accesses `app.style` which iterates all components' `scoped_style`.

### Steps

1. Open `webcompy/router/_view.py`.
2. Add import: `from webcompy._browser._modules import browser`.
3. Change `RouterView` base class from `Element` to `DynamicElement`.
4. Remove the duplicate `RouterPage` TypedDict from `_view.py` (it defines a `children` field for nested routing, duplicates `_pages.py`'s definition, and is not used by `Router.__init__` — it is dead code with no active change planning nested routing).
5. Rewrite `RouterView.__init__()`:
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
   ```
6. Implement `RouterView._on_set_parent()`:
   ```python
   def _on_set_parent(self):
       self._children = [self._switch]
       self._switch._parent = self
       if not browser:
           self._switch._on_set_parent()
           if self._router._preload:
               self._router.preload_lazy_routes()
       else:
           if self._router._preload:
               def _schedule_preload():
                   self._router.preload_lazy_routes()
               browser.window.setTimeout(_schedule_preload, 0)
   ```
7. Update imports in `_view.py`: replace `Element` import with `DynamicElement`.
8. Remove `ComponentGenerator` and `RouterContext` imports from `_view.py` (no longer needed after removing the duplicate TypedDict).
9. Open `webcompy/router/_router.py`.
10. Add `preload: bool = True` parameter to `Router.__init__()`, store as `self._preload`.
11. Implement `Router.preload_lazy_routes(self) -> None`:
   - Iterate over `self.__routes__` (each is a `RouteType` tuple).
   - For each `route`, get `component = route[3]`.
   - Check `isinstance(component, LazyComponentGenerator) and component._resolved is None`.
   - If browser environment (`from webcompy._browser._modules import browser`):
     - `browser.window.setTimeout(component._preload, 0)` — use a closure to capture the component reference correctly.
   - If non-browser (`browser is None`):
     - Call `component._preload()` immediately.
   - Guard: if `self._preload is False`, return early without preloading.
12. Implement `Router._get_component_for_path(self, path: str) -> ComponentGenerator | None`:
   - Strip leading/trailing slashes and base_url from `path`.
   - Iterate over `self.__routes__`, call each route's matcher function (`route[1]`) on `clean_path`.
   - Return `route[3]` (the `ComponentGenerator`) for the first match.
   - Return `None` if no match.
13. Run lint, typecheck, and tests.

### Acceptance Criteria

- `RouterView` is a `DynamicElement` subclass, not `Element`.
- `RouterView` does NOT produce a DOM node (no `<div webcompy-routerview>` wrapper).
- `RouterView._on_set_parent()` initializes children and schedules preload.
- `Router(preload=True)` (default) auto-preloads all lazy routes after initial render.
- `Router(preload=False)` skips auto-preload.
- `Router.preload_lazy_routes()` resolves unresolved `LazyComponentGenerator` instances.
- In browser, preloading uses `setTimeout(0)`.
- In SSG (non-browser), preloading happens immediately.
- `Router._get_component_for_path()` returns the correct `ComponentGenerator` for a matched path, `None` for unmatched.
- Existing E2E tests pass (the removed `<div>` should not break any selectors).
- SSG output is correct (no missing content due to removed wrapper div).
- The unused duplicate `RouterPage` TypedDict in `_view.py` is removed.

### Key File Paths

- `webcompy/router/_view.py` — refactor `RouterView` from `Element` to `DynamicElement`
- `webcompy/router/_router.py` — add `preload` param, `preload_lazy_routes()`, `_get_component_for_path()`
- `webcompy/router/_lazy.py` — `LazyComponentGenerator` (import for `isinstance` check)
- `webcompy/elements/types/_dynamic.py` — `DynamicElement` base class
- `webcompy/elements/types/_switch.py` — `SwitchElement` (child of RouterView)

### Important Notes

- `_get_component_for_path()` must handle `base_url` stripping for `mode="history"` the same way `_get_elements_generator()` does.
- `setTimeout` closures must capture the correct component reference — use default argument binding (`def _do(c=component): c._preload()`).
- The `_view.py` duplicate `RouterPage` TypedDict (lines 13-19) is not the one used by `Router.__init__` (that one is in `_pages.py`). It can be safely removed.
- SSG calls `app.set_path()` for each route before `generate_html()`. Combined with `preload_lazy_routes()` (immediate in non-browser), all `scoped_style` values will be available when `app.style` is accessed during HTML generation.

---

- [x] **Task 3: Add RouterLink hover preloading**

**Estimated time: ~1 hour**

### Context

`TypedRouterLink` extends `Element`, which accepts `events` (dict of `{event_name: handler}`) that translates to `addEventListener` calls in the browser. Currently, `RouterLink.__init__` passes `events={"click": self._on_click}`. The mouseenter handler must also go through this `events` dict, NOT through `attrs` (attrs set DOM attribute strings via `setAttribute`, which does not work for event handlers).

`self._to` can be either `str` or `SignalBase[str]`. The path value must be extracted before calling `_get_component_for_path()`. Query and hash portions of the path must be stripped before matching.

`self._router` is available as an instance attribute (injected via DI in `__init__`).

### Steps

1. Open `webcompy/router/_link.py`.
2. Add `_on_mouseenter` method to `TypedRouterLink`:
   ```python
   def _on_mouseenter(self, _ev=None):
       to_path = self._to.value if isinstance(self._to, SignalBase) else self._to
       path = to_path.split("?")[0].split("#")[0]
       if self._router.__mode__ == "history" and self._router.__base_url__:
           path = self._router._base_url_stripper(path)
       target = self._router._get_component_for_path(path)
       if isinstance(target, LazyComponentGenerator):
           target._preload()
   ```
3. Update `super().__init__()` call in `TypedRouterLink.__init__()`:
   - Change `events={"click": self._on_click}` to `events={"click": self._on_click, "mouseenter": self._on_mouseenter}`.
4. Update `self._event_handlers` in `_refresh()` (line 69):
   - Change `{"click": self._on_click}` to `{"click": self._on_click, "mouseenter": self._on_mouseenter}`.
5. Import `LazyComponentGenerator` from `webcompy.router._lazy` for `isinstance` check.
6. Run lint, typecheck, and tests.

### Acceptance Criteria

- Hovering over a `RouterLink` to a lazy route triggers `_preload()`.
- Hovering over a `RouterLink` to an eager route does nothing extra (no error, no exception).
- Clicking the link shortly after hover results in instant navigation.
- `mouseenter` handler is also updated during `_refresh()`.
- Works correctly in both `hash` and `history` routing modes.

### Key File Paths

- `webcompy/router/_link.py:37-65` — `TypedRouterLink.__init__()` — add mouseenter to `events` dict
- `webcompy/router/_link.py:67-71` — `_refresh()` — update `_event_handlers`
- `webcompy/router/_router.py` — `_get_component_for_path()` (added in Task 2)

### Important Notes

- Do NOT add `@mouseenter` to `_generate_attrs()` — attrs are DOM attribute strings set via `setAttribute`. Event handlers must go through the `events` parameter which uses `addEventListener`.
- The `mouseenter` handler must handle the case where `_get_component_for_path()` returns `None` (no route match) — the `isinstance(target, LazyComponentGenerator)` check returns `False` for `None`.
- In SSR/SSG (`browser is None`), `Element.__init__` still registers event handlers in `_event_handlers` dict, but they are never attached to DOM nodes. The `_on_mouseenter` method itself is harmless.
- No `mouseleave` handler is needed — preloading is a one-way operation with no visual side effects.

---

- [x] **Task 4: Add unit tests for lazy routing**

**Estimated time: ~1.5 hours**

### Context

Testing `LazyComponentGenerator._resolve()` requires creating a module with a `ComponentGenerator` attribute that can be imported via `importlib.import_module()`. Since `define_component` requires a DI scope (for `_try_register`), tests must set up a `DIScope` with a `ComponentStore` before creating test components.

### Steps

1. Create `tests/test_lazy_routing.py`.
2. Test `lazy()` validation:
   - `test_lazy_invalid_import_path_missing_colon`: `lazy("DocsPage", __file__)` → `WebComPyRouterException`.
   - `test_lazy_empty_module_path`: `lazy(":DocsPage", __file__)` → `WebComPyRouterException`.
   - `test_lazy_empty_attribute_name`: `lazy("myapp.pages:", __file__)` → `WebComPyRouterException`.
   - `test_lazy_empty_caller_file`: `lazy("myapp.pages:DocsPage", "")` → `WebComPyRouterException`.
   - `test_lazy_returns_component_generator`: `isinstance(lazy("module:Attr", __file__), ComponentGenerator)` → True.
3. Test `LazyComponentGenerator._resolve()`:
   - Create a temporary Python package with a `ComponentGenerator` attribute using `sys.modules` injection and `types.ModuleType`.
   - `test_lazy_resolve_imports_module`: Call `_resolve()` on a `LazyComponentGenerator` pointing to a known component, verify the returned `ComponentGenerator` matches.
   - `test_lazy_resolve_non_component_generator`: Configure a module with a non-component attribute, call `_resolve()` → `WebComPyRouterException`.
   - `test_lazy_resolve_caches_result`: Call `_resolve()` twice, verify `import_module` is called only once (check `self._resolved` is set).
4. Test `LazyComponentGenerator.__call__()` delegation:
   - `test_lazy_call_delegates_to_resolved`: Call `lazy_gen(props)`, verify it returns a `Component` instance.
5. Test `_preload()`:
   - `test_lazy_preload_without_rendering`: Call `_preload()`, verify `_resolved` is set but no `Component` is created.
6. Test `scoped_style` delegation:
   - `test_lazy_scoped_style_getter`: Access `scoped_style` on unresolved generator → triggers resolve.
   - `test_lazy_scoped_style_setter`: Set `scoped_style` on lazy generator → delegates to resolved.
7. Test `RouterView` as `DynamicElement`:
   - `test_router_view_is_dynamic_element`: Assert `isinstance(RouterView(), DynamicElement)`.
   - `test_router_view_has_no_dom_node`: Verify RouterView does not create a DOM element node.
8. Test `Router.preload_lazy_routes()`:
   - `test_router_preload_lazy_routes_browser`: Mock `browser.window.setTimeout`, verify it's called for each unresolved lazy route.
   - `test_router_preload_lazy_routes_ssg`: Without browser, verify `_preload()` is called immediately.
   - `test_router_preload_disabled`: `Router(preload=False)`, verify no preloading occurs.
9. Test `Router._get_component_for_path()`:
   - `test_get_component_for_path_match`: Verify correct component returned for a known path.
   - `test_get_component_for_path_no_match`: Verify `None` for an unknown path.
10. Run `uv run python -m pytest tests/test_lazy_routing.py --tb=short`.

### Acceptance Criteria

- All tests pass.
- Tests cover: lazy creation, validation, resolution, caching, delegation, preloading, RouterView refactor, Router integration.

---

- [ ] **Task 5: Convert docs_src routes to use lazy routing**

**Estimated time: ~1 hour**

### Context

`docs_src/router.py` currently imports all page modules eagerly and passes `ComponentGenerator` objects directly to `Router()`. After Task 2, `RouterView` no longer produces a `<div webcompy-routerview>` wrapper. E2E tests should be verified to not depend on this DOM structure.

The `docs_src` package structure:
- `docs_src/pages/home.py` → `HomePage`
- `docs_src/pages/document/home.py` → `DocumentHomePage`
- `docs_src/pages/demo/helloworld.py` → `HelloWorldPage`
- `docs_src/pages/demo/fizzbuzz.py` → `FizzbuzzPage`
- `docs_src/pages/demo/todo.py` → `ToDoListPage`
- `docs_src/pages/demo/matplotlib_sample.py` → `MatpoltlibSamplePage`
- `docs_src/pages/demo/fetch_sample.py` → `FetchSamplePage`
- `docs_src/pages/not_found.py` → `NotFound`

### Steps

1. Open `docs_src/router.py`.
2. Update imports: remove all page module imports except `HomePage`. Add `from webcompy.router import Router, lazy`.
3. Rewrite route definitions:
   ```python
   from webcompy.router import Router, lazy

   from .pages.home import HomePage
   from .pages.not_found import NotFound

   router = Router(
       {"path": "/", "component": HomePage},
       {"path": "/documents", "component": lazy("docs_src.pages.document.home:DocumentHomePage", __file__)},
       {"path": "/sample/helloworld", "component": lazy("docs_src.pages.demo.helloworld:HelloWorldPage", __file__)},
       {"path": "/sample/fizzbuzz", "component": lazy("docs_src.pages.demo.fizzbuzz:FizzbuzzPage", __file__)},
       {"path": "/sample/todo", "component": lazy("docs_src.pages.demo.todo:ToDoListPage", __file__)},
       {"path": "/sample/matplotlib", "component": lazy("docs_src.pages.demo.matplotlib_sample:MatpoltlibSamplePage", __file__)},
       {"path": "/sample/fetch", "component": lazy("docs_src.pages.demo.fetch_sample:FetchSamplePage", __file__)},
       default=NotFound,
       mode="history",
       base_url="",
   )
   ```
4. Start dev server: `uv run python -m webcompy start --dev --app docs_src.bootstrap:app`.
5. Verify manually:
   - Home page loads correctly.
   - No errors on initial load.
   - Navigation to each lazy page works correctly.
6. Run existing E2E tests: `uv run python -m pytest tests/e2e/ --tb=short`.

### Acceptance Criteria

- `docs_src` app works with lazy routing.
- Home page loads without errors.
- Navigation to all lazy routes works correctly.
- No console errors.
- Existing E2E tests pass (including after RouterView wrapper div removal).

### Key File Paths

- `docs_src/router.py` — update route definitions
- `docs_src/bootstrap.py` — entry point (no changes needed)

---

- [ ] **Task 6: Add SSG compatibility validation**

**Estimated time: ~0.5 hours**

### Context

SSG generates HTML by calling `app.set_path(path)` for each route, then `generate_html()` to produce the output. `generate_html()` accesses `app.style` which iterates `ComponentStore.components.values()` and reads each component's `scoped_style`. After the RouterView refactor, the SSG output no longer contains a `<div webcompy-routerview>` wrapper — the route content is rendered directly.

The SSG pipeline sequence is:
1. `app.set_path(path)` → triggers `SwitchElement._refresh()` → `LazyComponentGenerator.__call__()` → `_resolve()`.
2. `preload_lazy_routes()` → resolves remaining lazy routes immediately.
3. `generate_html()` → accesses `app.style` → all `scoped_style` values available.

### Steps

1. Run `uv run python -m webcompy generate --app docs_src.bootstrap:app`.
2. Check that `dist/` is created with all route directories.
3. For each route, verify the HTML output contains the expected component content (not blank/empty).
4. Verify the `<style>` tag in generated HTML contains CSS from all components (including lazy ones).
5. Verify no `<div webcompy-routerview>` in generated HTML (removed by RouterView refactor).
6. Run the E2E static site test: `uv run python -m pytest tests/e2e/test_static_site.py --tb=short`.

### Acceptance Criteria

- SSG output is correct for all routes (no blank pages or missing components).
- `<style>` tag contains scoped CSS from all lazy route components.
- No `<div webcompy-routerview>` in generated HTML.
- Static site E2E test passes.

---

## Dependencies

- Task 0 is a prerequisite for Task 1 (attribute rename enables subclass access).
- Task 1 is a prerequisite for Tasks 2, 3, 4, 5, 6.
- Task 2 is a prerequisite for Tasks 3, 4, 5, 6.
- Task 3 depends on Tasks 1 and 2.
- Task 4 depends on Tasks 1, 2, 3.
- Task 5 depends on Tasks 1, 2, 3 (all lazy routing code must be implemented).
- Task 6 depends on Task 5 (SSG validation requires lazy routes in docs_src).

## Specs to Update

- `openspec/specs/router/spec.md` — add `lazy()` function, `LazyComponentGenerator`, `RouterView` as `DynamicElement`, auto-preload, `RouterLink` hover preloading, `Router.preload` parameter, `ComponentGenerator` attribute rename
- `openspec/specs/components/spec.md` — add `ComponentGenerator` attribute rename requirement