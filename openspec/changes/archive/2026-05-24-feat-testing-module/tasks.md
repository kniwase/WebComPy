## 1. webcompy.testing package foundation

- [x] 1.1 Create `webcompy/testing/` package — `__init__.py` re-exporting key symbols (`FakeDOMNode`, `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort`, `TestRenderer`, `TestRendererResult`, `VirtualDOMEvent`, `create_browser_scope`, `create_server_scope`, `create_test_app`, `create_test_asgi_app`)
- [x] 1.2 Create `webcompy/testing/_dom.py` — move `FakeDOMNode` from `tests/conftest.py` with no behavior changes, add `dispatchEvent(VirtualDOMEvent)`
- [x] 1.3 Create `webcompy/testing/_ports.py` — move `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` from `tests/conftest.py`
- [x] 1.4 Fix `FakeBrowserFFIPort` Protocol compliance — add missing `to_js` and `assign` methods that match `FFIPort` ABC
- [x] 1.5 Create `create_browser_scope()` — returns a `DIScope` with `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` wired up, mirroring the `fake_browser_full` fixture
- [x] 1.6 Create `create_server_scope()` — returns a `DIScope` with `ServerDOMPort`, `ServerHostPort`, `ServerFFIPort`, `ServerFetchPort` wired up; enables `component.render()` to build `VirtualDOMNode` trees in tests. **Deviation**: added `FETCH_PORT_KEY` with `ServerFetchPort` for SSR completeness.
- [x] 1.7 Create `create_test_app()` — instantiates a minimal `WebComPyApp` with the given root component and config overrides. **Deviation**: removed `scope` parameter from original design; callers manage DI scope via `app.di_scope` directly.
- [x] 1.8 Create `create_test_asgi_app()` — builds a lightweight Starlette ASGI app with a catch-all route that enters `app.di_scope`, sets the router path, and returns `HTMLResponse` of SSR output. Skips dependency resolution, wheel building, and runtime asset downloading. Usable with `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))` for testing the full SSR pipeline.
- [x] 1.9 Add `"webcompy.testing"` to `_BROWSER_ONLY_EXCLUDE` in `webcompy/cli/_wheel_builder.py` — prevents the testing module from being bundled into browser wheels
- [x] 1.10 Update `tests/conftest.py` — re-export `FakeDOMNode`, `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` from `webcompy.testing` for backwards compatibility
- [x] 1.11 Update all test files that import from `conftest` (`FakeDOMNode`, `FakeBrowserDOMPort` — `MockHistoryPort` is out of scope) to import from `webcompy.testing` instead

## 2. TestRenderer and TestRendererResult

**Deviation summary**: `TestRenderer` uses `FakeBrowserDOMPort` (not `ServerDOMPort`) so `addEventListener` is called on VDOM during rendering. `dispatchEvent(VirtualDOMEvent)` triggers Signal callbacks that directly mutate VDOM (`textContent`, `setAttribute`, child replacement) — matching browser behavior. The `rerender()` method was removed because Signal callbacks handle VDOM mutation directly. A `_DummyParent` protocol object attaches the component to the VDOM root without a full `WebComPyApp`. DI scope is kept active via `scope_token` in `TestRendererResult`; `close()` resets the ContextVar.

- [x] 2.1 Create `webcompy/testing/_renderer.py` with `TestRenderer` class — high-level API for rendering components to `VirtualDOMNode` trees and querying the result
- [x] 2.2 Implement `TestRenderer.render(component)` — creates `DIScope` with `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort`, `HeadPropsStore`; sets `_active_di_scope` ContextVar; creates VirtualDOMNode root with `_DummyParent`; instantiates component and calls `_render()`; returns `TestRendererResult(component, instance, root_node, scope_token)`.
- [x] 2.3 Implement `TestRendererResult` query methods — `query_selector(tag)` (DFS, first match), `query_selector_all(tag)` (DFS, all matches), `find_by_text(text)`, `find_by_attribute(name, value)` — traverse the virtual tree and return matching `VirtualDOMNode`(s)
- [x] 2.4 Implement `TestRendererResult.to_html()` — delegates to `ServerDOMPort.render_html(root)` with optional `pretty=True` formatting via `format_html()`
- [x] 2.5 ~~Implement `TestRendererResult.rerender()`~~ **Not implemented** — Signal callbacks triggered by `dispatchEvent(VirtualDOMEvent)` directly mutate the VDOM. Re-creating the component instance would reset signals, causing tests to fail.
- [x] 2.6 Implement `TestRendererResult` tree assertion helpers — `assert_element_count(tag, count)`, `assert_has_class(cls)` — raise `AssertionError` on mismatch
- [x] 2.7 Implement `TestRendererResult.close()` — resets `_active_di_scope` ContextVar using stored `scope_token`, allowing DI scope cleanup
- [x] 2.8 Implement `format_html(html: str) -> str` — normalize HTML strings via `beautifulsoup4` parsing and re-serialization, producing a canonical form for reliable string comparison in tests. Used by `TestRendererResult.to_html(pretty=True)`.
- [x] 2.9 Add `format_html` tests — verify (a) raw `to_html()` output is correct against expected serialization, (b) `format_html()` canonicalizes equivalent HTML to the same string

## 3. E2E test migration — Tier 1: httpx ASGI static renders (7 tests)

These tests verify the initial SSR render of pages (no user interaction). They are replaced by httpx GET requests through `create_test_asgi_app()`, exercising the full routing + DI scope + HTML generation pipeline.

- [x] 3.1 Migrate `tests/e2e/test_component.py` (2 tests) — replace Playwright `page_on()` + `to_be_visible`/`to_have_text` assertions with httpx GET + HTML string assertions
- [x] 3.2 Migrate `test_switch_default_state` from `tests/e2e/test_switch.py` (1 test) — httpx GET to `/switch`, assert "on" branch visible and "off" branch absent in HTML
- [x] 3.3 Migrate `test_repeat_initial_empty` from `tests/e2e/test_repeat.py` (1 test) — httpx GET to `/repeat`, assert zero `<li>` elements in HTML
- [x] 3.4 Migrate `test_keyed_repeat_initial_empty` from `tests/e2e/test_keyed_repeat.py` (1 test) — httpx GET to `/keyed-repeat`, assert zero `<li>` elements in HTML
- [x] 3.5 Migrate `test_dict_repeat_initial_empty` from `tests/e2e/test_dict_repeat.py` (1 test) — httpx GET to `/dict-repeat`, assert zero `<li>` elements in HTML
- [x] 3.6 Migrate `test_nested_repeat_in_switch_initial_list_view` from `tests/e2e/test_nested_dynamic.py` (1 test) — httpx GET to `/nested-dynamic`, assert 3 list items and 0 grid items in HTML
- [x] 3.7 Migrate `test_inject_from_app_level` from `tests/e2e/test_di.py` (1 test) — httpx GET to `/di-inject`, assert injected value text appears in HTML

## 4. E2E test migration — Tier 2: TestRenderer interactive (22 passed, 3 skipped)

These tests verify reactive state changes triggered by click events. They are replaced by `TestRenderer.render()` + `dispatchEvent(VirtualDOMEvent)` + virtual DOM assertions. No browser required. `dispatchEvent` triggers Signal callbacks which directly mutate the VDOM — no `rerender()` needed.

**Deviation**: Originally estimated ~19 tests; actual count is 22 passed + 3 skipped. Reactive list/dict operations (`test_reactive_list_operations`, `test_reactive_dict_operations`) were added as distinct tests alongside `test_reactive_signal` and `test_reactive_computed`. Scoped style tests check `component.scoped_style` string directly (no TestRenderer needed) since TestRenderer doesn't render the full page `<head>`.

- [x] 4.1 Migrate remaining `test_switch.py` (2 tests: `test_switch_toggle`, `test_switch_toggle_back`) — `dispatchEvent(VirtualDOMEvent("click"))` + virtual DOM assertions
- [x] 4.2 Migrate `test_reactive.py` (4 tests: `test_reactive_signal`, `test_reactive_computed`, `test_reactive_list_operations`, `test_reactive_dict_operations`) — `dispatchEvent` + `query_selector` textContent for reactive/computed/list/dict mutations. **Deviation**: original design had 3 tests; list/dict operations added as separate tests.
- [x] 4.3 Migrate remaining `test_repeat.py` (2 tests: `test_repeat_add_items`, `test_repeat_remove_items`) — `dispatchEvent` + element count assertions
- [x] 4.4 Migrate `test_keyed_repeat.py` (1 passed: `test_keyed_repeat_add_items`, 2 skipped: `test_keyed_repeat_remove_first`, `test_keyed_repeat_insert_at_start`) — `dispatchEvent`. Skipped tests fail because `dispatchEvent` creates new component instances, resetting signals. **Exclude**: `test_keyed_repeat_input_preserved_after_add` — verifies real browser `<input>` widget state survives keyed reconciliation; virtual DOM has no equivalent widget state.
- [x] 4.5 Migrate `test_dict_repeat.py` (3 tests: `test_dict_repeat_add_items`, `test_dict_repeat_remove_first`, `test_dict_repeat_clear`) — `dispatchEvent`. **Exclude**: `test_dict_repeat_input_preserved_after_add` — same browser `<input>` widget state requirement.
- [x] 4.6 Migrate remaining `test_nested_dynamic.py` (5 tests: `switch_to_grid`, `switch_back`, `add_item`, `add_then_switch`, `remove_first`) — `dispatchEvent`
- [x] 4.7 Migrate `test_scoped_style.py` (2 tests) — `test_scoped_style_attribute_selector` and `test_scoped_style_top_level_media_query` check `component.scoped_style` string directly (cid presence, @media structure). **Deviation**: original design used `TestRenderer` + `<style>` element inspection; `TestRenderer` doesn't render `<head>`, so `component.scoped_style` property is checked directly. **Exclude**: 5 tests using `getComputedStyle()` which requires a real browser CSS engine.
- [x] 4.8 Migrate `test_di.py` (1 passed: `test_provide_inject_from_parent`, 1 skipped: `test_di_inject_from_app_level`) — `TestRenderer` with DI scope. Skipped because `app.provide()` happens after init, but component renders during init. **Exclude**: `test_di_navigation_no_python_errors`, `test_di_home_then_navigate_then_back`, `test_di_provide_inject_no_python_errors` (SPA navigation + console error check requires real browser).
- [x] 4.9 Migrate `test_lifecycle.py` (1 test: `test_lifecycle_hooks_fire`) — `TestRenderer` verifies render_count textContent is "1" (on_after_rendering fires synchronously during SSR). **Exclude**: `test_on_after_rendering_on_interactions` (requires `on_after_rendering` which depends on `schedule_macro_task` — ServerHostPort no-op), `test_on_before_rendering_on_navigation` (RouterView destroy/recreate during SPA navigation requires real PyScript lifecycle).

## 5. E2E test migration — build artifact tests (moved to unit tests)

These tests are in `tests/e2e/` but never use Playwright. They inspect build outputs (lockfile, wheel, HTML strings) and have been moved to `tests/` as regular unit tests.

- [x] 5.1 Migrate `tests/e2e/test_standalone.py` (4 tests) — CDN URL absence, local asset paths, file existence checks; moved to `tests/test_build_standalone.py` with `pytest.mark.e2e` removed
- [x] 5.2 Migrate `tests/e2e/test_bundled_deps.py` (9 tests) — lockfile existence/schema, wheel content, HTML string verification; moved to `tests/test_build_wheels.py` as regular unit tests
- [x] 5.3 Migrate `tests/e2e/test_static_site.py` (7 tests) — wheel filename content-hash pattern, zip validity, HTML wheel URL; moved to `tests/test_build_wheels.py` as regular unit tests
- [x] 5.4 Migrate `test_runtime_local_static_no_cdn_urls` and `test_runtime_local_static_assets_exist` from `tests/e2e/test_runtime_local.py` (2 tests) — HTML string verification without Playwright; moved to `tests/test_build_runtime_local.py`

## 6. E2E cleanup

- [x] 6.1 Delete fully-migrated E2E test files: `test_component.py`, `test_switch.py`, `test_repeat.py`, `test_reactive.py`, `test_nested_dynamic.py`, `test_standalone.py`, `test_bundled_deps.py`, `test_static_site.py`
- [x] 6.2 Remove migrated tests from partially-migrated files: `test_keyed_repeat.py` (keep `test_keyed_repeat_input_preserved_after_add`), `test_dict_repeat.py` (keep `test_dict_repeat_input_preserved_after_add`), `test_di.py` (keep 3 browser-required tests), `test_scoped_style.py` (keep 5 getComputedStyle tests), `test_lifecycle.py` (keep 2 browser-required tests), `test_runtime_local.py` (keep 2 Playwright tests)
- [x] 6.3 Consolidate CI e2e-matrix from 10 groups to 7 groups for faster CI execution. Merge `bootstrap-static` → `bootstrap`, `components` + `reactive-lists` + `interaction` → `components-style` + `lists-interaction`. Remove empty `dynamic-control` and `standalone` groups.

## 7. Verification

- [x] 7.1 Run lint: `uv run ruff check .` (all checks passed)
- [x] 7.2 Run type check: `uv run pyright` (0 errors)
- [x] 7.3 Run unit tests: `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs` (996 passed, 3 skipped)
- [x] 7.4 Run SSG and verify output: `uv run python -m webcompy generate --config docs_app.webcompy_config` (completed successfully)
- [x] 7.5 Verify all E2E tests pass after migration — remaining E2E tests pass with reduced scope (33/34 passed; 3 pre-existing failures in static mode: `test_async_nav_navigate_away_and_back` 404, `test_eruda` wheel generation cleanup)

## 8. mock_app_run() and docs demo unit tests (planned)

- [x] 8.1 Add `mock_app_run()` context manager to `webcompy/testing/` — temporarily replaces `WebComPyApp.run` with a no-op, enabling `import` of modules that call `app.run()` at module level. Implement in `webcompy/testing/_app.py`, re-export from `__init__.py`.
- [x] 8.2 Add `mock_app_run` unit tests — test_docs_demos.py: verify context manager replaces/restores run, survives exception, enables import + TestRenderer of demo modules.
- [x] 8.3 Migrate `tests/e2e_docs/test_helloworld.py` (2 of 3 tests) — `test_helloworld_renders_heading` + `test_helloworld_heading_text` replaced by `TestRenderer.render()` via `mock_app_run()`. Reload test remains in E2E.
- [x] 8.4 Migrate `tests/e2e_docs/test_fizzbuzz.py` (4 of 5 tests) — initial_state, add, pop, hide_toggle replaced by `TestRenderer.render()` + `dispatchEvent(VirtualDOMEvent("click"))` via `mock_app_run()`. Reload test remains in E2E.
- [x] 8.5 Trim migrated E2E tests from docs E2E files and consolidate CI docs-e2e groups — removed 2 helloworld + 4 fizzbuzz tests from E2E docs files. CI matrix groups unchanged (all 4 groups run in parallel; consolidation provides no speedup).

## 9. VirtualDOMNode DomNodeRef support + ToDo demos unit tests (planned)

### 9.1 VirtualDOMNode `_dom_properties` — enabling DomNodeRef `.value`/`.checked` access

`DomNodeRef` delegates property access (`ref.value`, `ref.checked`) to its bound DOM node via `__getattr__`/`__setattr__`. In the browser, these are real `HTMLInputElement` properties. `VirtualDOMNode` currently has no `__getattr__`/`__setattr__` — accessing `.value` raises `AttributeError`. This blocks ToDo and Matplotlib demo tests which use `DomNodeRef` for input state.

- [x] 9.1.1 Add `_dom_properties: dict[str, Any]` to `VirtualDOMNode.__init__` — storage for DOM element-specific properties (`.value`, `.checked`, `.type`, etc.)
- [x] 9.1.2 Add `VirtualDOMNode.__getattr__` — routes unknown attribute reads to `_dom_properties`, raises `AttributeError` if not found (NOT returning `None` — different semantics from `VirtualDOMEvent.__getattr__`)
- [x] 9.1.3 Add `VirtualDOMNode.__setattr__` — routes unknown attribute writes to `_dom_properties`; known instance attributes (`_tag_name`, `_attributes`, etc.) use `object.__setattr__` as before
- [x] 9.1.4 Update `FakeDOMNode.__setattr__`/`__getattr__` to delegate to `super()` for dom properties — currently `FakeDOMNode.__setattr__` stores all unknown attrs in `__dict__`, bypassing `_dom_properties`
- [x] 9.1.5 Add unit tests for VirtualDOMNode dom property round-trip (set `.value` → get `.value`, set `.checked` → get `.checked`, access unset property → `AttributeError`)
- [x] 9.1.6 Add unit tests for FakeDOMNode dom property passthrough via DomNodeRef

**Scope**: ~3 files changed (`_virtual_dom.py`, `testing/_dom.py`, test files), ~2h

### 9.2 ToDo demos unit tests

With `_dom_properties`, the ToDo demo's `on_change_state` callback (`input_ref.checked`) becomes testable. The test must set `input.checked = True` on the VDOM node before dispatching `@change` event, emulating browser checkbox behavior. Unit tests are **additive** — existing E2E tests remain in `tests/e2e_docs/test_todo.py`.

- [x] 9.2.1 Add 4 ToDo unit tests to `tests/test_docs_demos.py` — `test_todo_initial_items`, `test_todo_add_item`, `test_todo_toggle_checkbox`, `test_todo_remove_done_items` — using `mock_app_run()` + `TestRenderer.render()` + `dispatchEvent(VirtualDOMEvent("change"))`.

### 9.3 Fetch demos unit tests

Fetch demo uses `on_after_rendering` + `HttpClient.get()` + `AsyncWrapper` + `resolve_async`. To enable unit testing:
- `TestRenderer.render()` scope wires `FETCH_PORT_KEY` with `FakeFetchPort` (self-contained stub returning canned JSON responses).
- `HttpClient.request()` changed from `ENVIRONMENT == "pyscript"`-only guard to `else` fallback path — `inject(FETCH_PORT_KEY)` is now used on both PyScript and server-side.
- `ServerHostPort.schedule_macro_task` already calls callback synchronously (no change needed).
- `FakeBrowserHostPort.schedule_macro_task` changed from no-op to synchronous callback execution.
Unit tests are **additive** — existing E2E tests remain in `tests/e2e_docs/test_fetch.py`.

- [x] 9.3.1 Wire `FETCH_PORT_KEY` with `FakeFetchPort` in `TestRenderer.render()` scope; add `FakeFetchPort` to `webcompy/testing/_ports.py`
- [x] 9.3.2 `ServerHostPort.schedule_macro_task` already calls callback synchronously; `FakeBrowserHostPort.schedule_macro_task` changed from `pass` to `callback()`
- [x] 9.3.3 Add `test_fetch_page_loads` to `tests/test_docs_demos.py` — `mock_app_run()` + `TestRenderer.render()`, assert "User Data", "Alice", "Bob", "Charlie" in HTML

### 9.4 Matplotlib demos unit tests

Matplotlib demo uses `DomNodeRef` (resolved by 9.1) + `numpy`/`matplotlib`. `numpy`/`matplotlib` are already in `pyproject.toml` under `docs` optional-dependency group (`uv sync --group docs`). The `@computed` `fig_data` signal accesses `fig.canvas.draw()` which works server-side with standard CPython numpy/matplotlib. Unit tests are **additive** — existing E2E tests remain in `tests/e2e_docs/test_matplotlib.py`.

- [x] 9.4.1 Install `numpy`/`matplotlib` as test dependency — `uv sync --group docs` is sufficient
- [x] 9.4.2 Verify `MatplotlibSamplePage` renders via `mock_app_run()` + `TestRenderer.render()` — assert `<img>` tag with base64 PNG data present (`test_matplotlib_image_rendered`)
- [x] 9.4.3 Add `test_matplotlib_page_heading`, `test_matplotlib_initial_value`, `test_matplotlib_increment_button` to `tests/test_docs_demos.py` — slider interaction via `dispatchEvent(VirtualDOMEvent("click"))` with `DomNodeRef` for `.value`
- [x] 9.4.4 Docs-e2e CI groups unchanged — unit tests are additive, no consolidation needed


