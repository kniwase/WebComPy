## 1. webcompy.testing package foundation

- [x] 1.1 Create `webcompy/testing/` package — `__init__.py` re-exporting key symbols (`FakeDOMNode`, `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort`, `TestRenderer`, `TestRendererResult`, `VirtualDOMEvent`, `create_browser_scope`, `create_server_scope`, `create_test_app`, `create_test_asgi_app`)
- [x] 1.2 Create `webcompy/testing/_dom.py` — move `FakeDOMNode` from `tests/conftest.py` with no behavior changes, add `dispatchEvent(VirtualDOMEvent)`
- [x] 1.3 Create `webcompy/testing/_ports.py` — move `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` from `tests/conftest.py`
- [x] 1.4 Fix `FakeBrowserFFIPort` Protocol compliance — add missing `to_js` and `assign` methods that match `FFIPort` ABC
- [x] 1.5 Create `create_browser_scope()` — returns a `DIScope` with `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` wired up, mirroring the `fake_browser_full` fixture
- [x] 1.6 Create `create_server_scope()` — returns a `DIScope` with `ServerDOMPort`, `ServerHostPort`, `ServerFFIPort` wired up; enables `component.render()` to build `VirtualDOMNode` trees in tests
- [x] 1.7 Create `create_test_app()` — instantiates a minimal `WebComPyApp` with the given scope, enabling component rendering tests without a full server
- [x] 1.8 Create `create_test_asgi_app()` — builds a lightweight Starlette ASGI app with a catch-all route that enters `app.di_scope`, sets the router path, and returns `HTMLResponse` of SSR output. Skips dependency resolution, wheel building, and runtime asset downloading. Usable with `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))` for testing the full SSR pipeline.
- [x] 1.9 Add `"webcompy.testing"` to `_BROWSER_ONLY_EXCLUDE` in `webcompy/cli/_wheel_builder.py` — prevents the testing module from being bundled into browser wheels
- [x] 1.10 Update `tests/conftest.py` — re-export `FakeDOMNode`, `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` from `webcompy.testing` for backwards compatibility
- [x] 1.11 Update all test files that import from `conftest` (`FakeDOMNode`, `FakeBrowserDOMPort` — `MockHistoryPort` is out of scope) to import from `webcompy.testing` instead

## 2. TestRenderer and TestRendererResult

- [x] 2.1 Create `webcompy/testing/_renderer.py` with `TestRenderer` class — high-level API for rendering components to `VirtualDOMNode` trees and querying the result
- [x] 2.2 Implement `TestRenderer.render(component)` — monkeypatches `ENVIRONMENT` on element modules, creates server-side DI scope, instantiates minimal `WebComPyApp`, calls `component.render()`, returns `TestRendererResult(app, root_node, scope)`
- [x] 2.3 Implement `TestRendererResult` query methods — `query_selector(tag)` (DFS, first match), `query_selector_all(tag)` (DFS, all matches), `find_by_text(text)`, `find_by_attribute(name, value)` — traverse the virtual tree and return matching `VirtualDOMNode`(s)
- [x] 2.4 Implement `TestRendererResult.to_html()` — delegates to `ServerDOMPort.render_html(root)`
- [x] 2.5 Implement `TestRendererResult.rerender()` — re-executes component `render()` on the existing virtual root so that signal changes from `dispatchEvent(VirtualDOMEvent)` are reflected in the queryable tree
- [x] 2.6 Implement `TestRendererResult` tree assertion helpers — `assert_element_count(tag, count)`, `assert_has_class(cls)` — raise `AssertionError` on mismatch
- [x] 2.7 Implement `format_html(html: str) -> str` — normalize HTML strings via `beautifulsoup4` parsing and re-serialization, producing a canonical form for reliable string comparison in tests. Used by `TestRendererResult.to_html(pretty=True)`.
- [x] 2.8 Add `format_html` tests — verify (a) raw `to_html()` output is correct against expected serialization, (b) `format_html()` canonicalizes equivalent HTML to the same string

## 3. E2E test migration — Tier 1: httpx ASGI static renders (~7 tests)

These tests verify the initial SSR render of pages (no user interaction). They are replaced by httpx GET requests through `create_test_asgi_app()`, exercising the full routing + DI scope + HTML generation pipeline.

- [x] 3.1 Migrate `tests/e2e/test_component.py` (2 tests) — replace Playwright `page_on()` + `to_be_visible`/`to_have_text` assertions with httpx GET + HTML string assertions
- [x] 3.2 Migrate `test_switch_default_state` from `tests/e2e/test_switch.py` (1 test) — httpx GET to `/switch`, assert "on" branch visible and "off" branch absent in HTML
- [x] 3.3 Migrate `test_repeat_initial_empty` from `tests/e2e/test_repeat.py` (1 test) — httpx GET to `/repeat`, assert zero `<li>` elements in HTML
- [x] 3.4 Migrate `test_keyed_repeat_initial_empty` from `tests/e2e/test_keyed_repeat.py` (1 test) — httpx GET to `/keyed-repeat`, assert zero `<li>` elements in HTML
- [x] 3.5 Migrate `test_dict_repeat_initial_empty` from `tests/e2e/test_dict_repeat.py` (1 test) — httpx GET to `/dict-repeat`, assert zero `<li>` elements in HTML
- [x] 3.6 Migrate `test_nested_repeat_in_switch_initial_list_view` from `tests/e2e/test_nested_dynamic.py` (1 test) — httpx GET to `/nested-dynamic`, assert 3 list items and 0 grid items in HTML
- [x] 3.7 Migrate `test_inject_from_app_level` from `tests/e2e/test_di.py` (1 test) — httpx GET to `/di-inject`, assert injected value text appears in HTML

## 4. E2E test migration — Tier 2: TestRenderer interactive (~19 tests)

These tests verify reactive state changes triggered by click events. They are replaced by `TestRenderer.render()` + `dispatchEvent(VirtualDOMEvent)` + `rerender()` + virtual DOM assertions. No browser required.

- [ ] 4.1 Migrate remaining `test_switch.py` (2 tests: `test_switch_toggle`, `test_switch_toggle_back`) — `dispatchEvent(VirtualDOMEvent("click"))` + `rerender` + virtual DOM assertions
- [ ] 4.2 Migrate `test_reactive.py` (3 tests) — `dispatchEvent` + `rerender` + `query_selector` textContent for reactive/computed/list/dict mutations
- [ ] 4.3 Migrate remaining `test_repeat.py` (2 tests: `test_repeat_add_items`, `test_repeat_remove_items`) — `dispatchEvent` + `rerender` + element count assertions
- [ ] 4.4 Migrate `test_keyed_repeat.py` (3 of 5 tests: `test_keyed_repeat_add_items`, `test_keyed_repeat_remove_first`, `test_keyed_repeat_insert_at_start`) — `dispatchEvent` + `rerender`. **Exclude**: `test_keyed_repeat_input_preserved_after_add` — verifies real browser `<input>` widget state survives keyed reconciliation; virtual DOM has no equivalent widget state.
- [ ] 4.5 Migrate `test_dict_repeat.py` (3 of 5 tests: `test_dict_repeat_add_items`, `test_dict_repeat_remove_first`, `test_dict_repeat_clear`) — `dispatchEvent` + `rerender`. **Exclude**: `test_dict_repeat_input_preserved_after_add` — same browser `<input>` widget state requirement.
- [ ] 4.6 Migrate remaining `test_nested_dynamic.py` (5 tests: `switch_to_grid`, `switch_back`, `add_item`, `add_then_switch`, `remove_first`) — `dispatchEvent` + `rerender`
- [ ] 4.7 Migrate `test_scoped_style.py` (2 of 7 tests) — `test_scoped_style_attribute_selector` and `test_scoped_style_top_level_media_query` only check `<style>` element `textContent` against virtual DOM. **Exclude**: 5 tests using `getComputedStyle()` which requires a real browser CSS engine.
- [ ] 4.8 Migrate `test_di.py` (1 test: `test_provide_inject_from_parent`) — `TestRenderer` with DI scope. **Exclude**: `test_di_navigation_no_python_errors` and `test_di_home_then_navigate_then_back` (SPA navigation + console error check), `test_di_provide_inject_no_python_errors` (browser console check).
- [ ] 4.9 Migrate `test_lifecycle.py` (1 test: `test_lifecycle_hooks_fire`) — `TestRenderer` with server scope (on_before_rendering fires synchronously during SSR). **Exclude**: `test_on_after_rendering_on_interactions` (requires `on_after_rendering` which depends on `schedule_macro_task` — ServerHostPort no-op), `test_on_before_rendering_on_navigation` (RouterView destroy/recreate during SPA navigation requires real PyScript lifecycle).

## 5. E2E test migration — build artifact tests (moved to unit tests)

These tests are in `tests/e2e/` but never use Playwright. They inspect build outputs (lockfile, wheel, HTML strings) and should be moved to `tests/` as regular unit tests.

- [ ] 5.1 Migrate `tests/e2e/test_standalone.py` (4 tests) — CDN URL absence, local asset paths, file existence checks; move to `tests/` with `pytest.mark.e2e` removed
- [ ] 5.2 Migrate `tests/e2e/test_bundled_deps.py` (9 tests) — lockfile existence/schema, wheel content, HTML string verification; move to `tests/` as regular unit tests
- [ ] 5.3 Migrate `tests/e2e/test_static_site.py` (7 tests) — wheel filename content-hash pattern, zip validity, HTML wheel URL; move to `tests/`
- [ ] 5.4 Migrate `test_runtime_local_no_cdn_urls` and `test_runtime_local_static_assets_exist` from `tests/e2e/test_runtime_local.py` (2 tests) — HTML string verification without Playwright; move to `tests/`

## 6. Verification

- [ ] 6.1 Run lint: `uv run ruff check .`
- [ ] 6.2 Run type check: `uv run pyright`
- [ ] 6.3 Run unit tests: `uv run python -m pytest tests/ --tb=short`
- [ ] 6.4 Run SSG and verify output: `uv run python -m webcompy generate --app docs_app.bootstrap:app`
- [ ] 6.5 Verify all E2E tests pass after migration — remaining E2E tests must still pass with reduced scope (browser-required tests stay in E2E)
- [ ] 6.6 Update CI e2e-matrix in `.github/workflows/ci.yml` if any E2E test files are removed or renamed
