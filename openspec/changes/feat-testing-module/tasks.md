## 1. webcompy.testing package foundation

- [ ] 1.1 Create `webcompy/testing/` package — `__init__.py` re-exporting key symbols (`FakeDOMNode`, `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort`, `TestRenderer`, `TestRendererResult`, `VirtualDOMEvent`, `create_browser_scope`, `create_server_scope`, `create_test_app`)
- [ ] 1.2 Create `webcompy/testing/_dom.py` — move `FakeDOMNode` from `tests/conftest.py` with no behavior changes, add `dispatchEvent(VirtualDOMEvent)`
- [ ] 1.3 Create `webcompy/testing/_ports.py` — move `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` from `tests/conftest.py`
- [ ] 1.4 Fix `FakeBrowserFFIPort` Protocol compliance — add missing `to_js` and `assign` methods that match `FFIPort` ABC
- [ ] 1.5 Create `create_browser_scope()` — returns a `DIScope` with `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` wired up, mirroring the `fake_browser_full` fixture
- [ ] 1.6 Create `create_server_scope()` — returns a `DIScope` with `ServerDOMPort`, `ServerHostPort`, `ServerFFIPort` wired up; enables `component.render()` to build `VirtualDOMNode` trees in tests
- [ ] 1.7 Create `create_test_app()` — instantiates a minimal `WebComPyApp` with the given scope, enabling component rendering tests without a full server
- [ ] 1.8 Add `"webcompy.testing"` to `_BROWSER_ONLY_EXCLUDE` in `webcompy/cli/_wheel_builder.py` — prevents the testing module from being bundled into browser wheels
- [ ] 1.9 Update `tests/conftest.py` — re-export `FakeDOMNode`, `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` from `webcompy.testing` for backwards compatibility
- [ ] 1.10 Update all test files that import from `conftest` (`FakeDOMNode`, `FakeBrowserDOMPort` — `MockHistoryPort` is out of scope) to import from `webcompy.testing` instead

## 2. TestRenderer and TestRendererResult

- [ ] 2.1 Create `webcompy/testing/_renderer.py` with `TestRenderer` class — high-level API for rendering components to `VirtualDOMNode` trees and querying the result
- [ ] 2.2 Implement `TestRenderer.render(component)` — monkeypatches `ENVIRONMENT` on element modules, creates server-side DI scope, instantiates minimal `WebComPyApp`, calls `component.render()`, returns `TestRendererResult(app, root_node, scope)`
- [ ] 2.3 Implement `TestRendererResult` query methods — `query_selector(tag)` (DFS, first match), `query_selector_all(tag)` (DFS, all matches), `find_by_text(text)`, `find_by_attribute(name, value)` — traverse the virtual tree and return matching `VirtualDOMNode`(s)
- [ ] 2.4 Implement `TestRendererResult.to_html()` — delegates to `ServerDOMPort.render_html(root)`
- [ ] 2.5 Implement `TestRendererResult.rerender()` — re-executes component `render()` on the existing virtual root so that signal changes from `dispatchEvent(VirtualDOMEvent)` are reflected in the queryable tree
- [ ] 2.6 Implement `TestRendererResult` tree assertion helpers — `assert_element_count(tag, count)`, `assert_has_class(cls)` — raise `AssertionError` on mismatch

## 3. E2E test migration — purely rendering (24 tests)

- [ ] 3.1 Migrate `tests/e2e/test_component.py` (2 tests) — replace `to_be_visible`/`to_have_text` with `TestRenderer.render()` + `query_selector` + `textContent`; component text content is fully verifiable via `VirtualDOMNode`
- [ ] 3.2 Migrate `tests/e2e/test_standalone.py` (4 tests) — CDN URL absence, local asset paths, file existence checks; no Playwright usage, move to `tests/` with `pytest.mark.e2e` removed
- [ ] 3.3 Migrate `tests/e2e/test_bundled_deps.py` (9 tests) — lockfile existence/schema, wheel content, HTML string verification; no Playwright usage, move to `tests/` as regular unit tests
- [ ] 3.4 Migrate `tests/e2e/test_static_site.py` (7 tests) — wheel filename content-hash pattern, zip validity, HTML wheel URL; no Playwright usage, move to `tests/`
- [ ] 3.5 Migrate `test_runtime_local_no_cdn_urls` and `test_runtime_local_static_assets_exist` from `tests/e2e/test_runtime_local.py` (2 tests) — HTML string verification without Playwright

## 4. E2E test migration — interactive with TestRenderer (31 tests)

- [ ] 4.1 Migrate `test_switch.py` (3 tests) — all tests use only click events; `dispatchEvent(VirtualDOMEvent("click"))` replaces Playwright `click()`. Default state, toggle on, toggle off all work via `TestRenderer` + `rerender` + virtual DOM assertions.
- [ ] 4.2 Migrate `test_reactive.py` (3 tests) — text update, list operations, dict operations all triggered by button clicks ignoring event arg. dispatchEvent + rerender + virtual tree assertions fully cover.
- [ ] 4.3 Migrate `test_repeat.py` (3 tests) — initial empty state (no interaction) plus add/remove via clicks. dispatchEvent covers all interactive assertions.
- [ ] 4.4 Migrate `test_keyed_repeat.py` (4 of 5 tests) — initial empty, add items, remove first, insert at start all use click-only handlers. **Exclude**: `test_keyed_repeat_input_preserved_after_add` — verifies real browser `<input>` widget state survives keyed reconciliation; virtual DOM has no equivalent widget state.
- [ ] 4.5 Migrate `test_dict_repeat.py` (4 of 5 tests) — same pattern as keyed repeat. **Exclude**: `test_dict_repeat_input_preserved_after_add` — same browser `<input>` widget state requirement.
- [ ] 4.6 Migrate `test_nested_dynamic.py` (6 tests) — all tests (initial view, switch to grid, switch back, add item, add then switch, remove first) use click-only handlers. dispatchEvent + rerender covers all.
- [ ] 4.7 Migrate `test_scoped_style.py` (2 of 7 tests) — `test_scoped_style_attribute_selector` and `test_scoped_style_top_level_media_query` only check `<style>` element `textContent` against virtual DOM. **Exclude**: 5 tests using `getComputedStyle()` which requires a real browser CSS engine.
- [ ] 4.8 Migrate `test_di.py` (4 of 5 tests) — `test_provide_inject_from_parent` and `test_inject_from_app_level` can render DI components directly via TestRenderer with proper DI scope set up. `test_di_navigation_no_python_errors` and `test_di_home_then_navigate_then_back` use RouterLink navigation which is now testable via dispatchEvent (after `feat-virtual-dom` RouterLink fix); `assert_no_console_errors` replaced by exception assertion. **Exclude**: `test_di_provide_inject_no_python_errors` — requires `assert_no_console_errors`.
- [ ] 4.9 Migrate `test_lifecycle.py` (2 of 3 tests) — `test_lifecycle_hooks_fire` and `test_on_after_rendering_on_interactions` use click-only handler or no interaction. **Exclude**: `test_on_before_rendering_on_navigation` — depends on RouterView destroy/recreate cycle during navigation (requires real PyScript lifecycle).

## 5. Verification

- [ ] 5.1 Run lint: `uv run ruff check .`
- [ ] 5.2 Run type check: `uv run pyright`
- [ ] 5.3 Run unit tests: `uv run python -m pytest tests/ --tb=short`
- [ ] 5.4 Run SSG and verify output: `uv run python -m webcompy generate --app docs_app.bootstrap:app`
- [ ] 5.5 Verify all E2E tests pass after migration — remaining E2E tests must still pass with reduced scope (browser-required tests stay in E2E)
- [ ] 5.6 Update CI e2e-matrix in `.github/workflows/ci.yml` if any E2E test files are removed or renamed
