## 1. VirtualDOMNode implementation

- [ ] 1.1 Create `webcompy/ports/_server/_virtual_dom.py` with `VirtualDOMNode` class satisfying `DOMNode` Protocol — store `tag_name`, `attributes: dict`, `children: list`, `event_listeners: list`, `text_content`, `node_type`, `__webcompy_node__`, `_parent`
- [ ] 1.2 Implement tree operations: `appendChild`, `removeChild`, `insertBefore`, `replaceChild`, `remove` — manage children list and parent references
- [ ] 1.3 Implement attribute operations: `setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`
- [ ] 1.4 Implement event operations: `addEventListener`, `removeEventListener` — store as `(event_name, handler)` tuples
- [ ] 1.5 Implement `dispatchEvent(event: MockDOMEvent) -> None` — fire stored handlers matching `event.type` synchronously so that signal updates and re-rendering propagate within the same call stack
- [ ] 1.6 Create `MockDOMEvent` class in `webcompy/testing/_dom.py` — minimal `type`, `target`, `currentTarget`, `preventDefault` for use with `VirtualDOMNode.dispatchEvent()`
- [ ] 1.7 Implement properties: `childNodes` (returns list), `textContent` (get/set), `nodeName` (returns tag_name), `nodeType` (1=element, 3=text)

## 2. ServerDOMPort rewrite

- [ ] 2.1 Rewrite `webcompy/ports/_server/_dom.py` — replace exception-throwing stubs with virtual DOM factory: `create_element()` returns `VirtualDOMNode`, `create_text_node()` returns virtual text node
- [ ] 2.2 Implement `ServerDOMPort.render_html(node: DOMNode) -> str` — traverse virtual tree, serialize to HTML string
- [ ] 2.3 Implement HTML serialization rules: HTML-escape text content and attribute values, output void elements without closing tags (e.g., `<br>`, `<img>`) per HTML5 convention, omit `None`-valued attributes
- [ ] 2.4 Verify `render_html()` produces identical output to current `_render_html()` methods — generate docs_app with both paths and diff results

## 3. webcompy.testing module

- [ ] 3.1 Create `webcompy/testing/` package — `__init__.py` re-exporting key symbols, `_dom.py` for `FakeDOMNode`, `_ports.py` for port fakes, helper for pre-wired `DIScope`
- [ ] 3.2 Move `FakeDOMNode` from `tests/conftest.py` to `webcompy/testing/_dom.py` — no behavior changes, just relocation
- [ ] 3.3 Fix `FakeBrowserFFIPort` Protocol compliance — add missing `to_js` and `assign` methods that match `FFIPort` ABC
- [ ] 3.4 Create `create_browser_scope()` helper — returns a `DIScope` with all browser-side fake ports (FakeBrowserDOMPort, FakeBrowserHostPort, FakeBrowserFFIPort) wired up, mirroring the `fake_browser_full` fixture
- [ ] 3.5 Create `create_server_scope()` helper — returns a `DIScope` with `ServerDOMPort` wired up; enables `component.render()` to build `VirtualDOMNode` trees in tests
- [ ] 3.6 Create `create_test_app()` helper — instantiates a minimal `WebComPyApp` with the given scope, enabling component rendering tests without a full server
- [ ] 3.7 Add `"webcompy.testing"` to `_BROWSER_ONLY_EXCLUDE` in `webcompy/cli/_wheel_builder.py` — prevents the testing module from being bundled into browser wheels
- [ ] 3.8 Update all test files that import from `conftest` (`FakeDOMNode`, `FakeBrowserDOMPort`, `MockHistoryPort` is out of scope) to import from `webcompy.testing` instead
- [ ] 3.9 Remove `FakeDOMNode`, `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` from `tests/conftest.py` — replaced by imports from `webcompy.testing`
- [ ] 3.10 Create `webcompy/testing/_renderer.py` with `TestRenderer` class — high-level API for rendering components to `VirtualDOMNode` trees and querying the result (jsdom-like for WebComPy)
- [ ] 3.11 Implement `TestRenderer.render(component)` — creates a `DIScope` with `ServerDOMPort`, calls `component.render()`, returns a `TestRendererResult` wrapping the virtual root node
- [ ] 3.12 Implement `TestRendererResult` query methods — `query_selector(tag)`, `query_selector_all(tag)`, `find_by_text(text)`, `find_by_attribute(name, value)`, `to_html()` — traverse the virtual tree and return matching `VirtualDOMNode`(s)
- [ ] 3.13 Implement `TestRendererResult` tree assertion helpers — `assert_element(tag, text=None)`, `assert_element_count(tag, count)`, `assert_has_class(cls)` — raise `AssertionError` on mismatch
- [ ] 3.14 Implement `TestRendererResult.rerender()` — re-executes component `render()` on the existing virtual root so that signal changes from `dispatchEvent()` are reflected in the queryable tree

## 4. Unify render path in element base classes

- [ ] 4.1 Remove `_render_html()` abstract method from `ElementAbstract` in `webcompy/elements/types/_abstract.py` — after cli/_html.py is migrated (task 6)
- [ ] 4.2 Remove `_render_html()` from `ElementWithChildren` in `webcompy/elements/types/_base.py`
- [ ] 4.3 Update `TextElement._update_text()` in `webcompy/elements/types/_text.py` — remove `if browser:` branch; both environments call `node.textContent = new_text` since `VirtualDOMNode` supports it
- [ ] 4.4 Remove `if not browser:` server branches from `_on_set_parent()` in element and router types — `_switch.py:84`, `_repeat.py:95`, `_view.py:25` (router). After virtual DOM unification, `render()` creates VirtualDOMNodes on the server via `ServerDOMPort`, so the server-only pre-creation logic inside these branches is no longer needed and would cause double creation
- [ ] 4.5 Verify that `_init_node()` (already unbranchified by `feat-port-abstraction`) works correctly with `VirtualDOMNode` on the server — both `ElementBase._init_node()` and `TextElement._init_node()` / `NewLine._init_node()` call `_create_node()` which delegates to `inject(DOM_PORT_KEY)` returning a `VirtualDOMNode`
- [ ] 4.6 Verify that `_detach_node()` (already unbranchified by `feat-port-abstraction`) works correctly with `VirtualDOMNode` on the server — `dom_port.create_text_node("")` returns a virtual text node and `parent_node.replaceChild(...)` operates on the virtual children list
- [ ] 4.7 Remove `if browser:` branch from `DynamicElement._render()` in `webcompy/elements/types/_dynamic.py` — after virtual DOM unification, `_position_element_nodes()` works on `VirtualDOMNode` (uses `appendChild`/`insertBefore` which `VirtualDOMNode` implements), so both environments use the same positioning logic
- [ ] 4.8 Remove environment guard from `RepeatElement._refresh()` in `webcompy/elements/types/_repeat.py:148` — change `if self._has_key and browser and self._children_keys:` to `if self._has_key and self._children_keys:`. After virtual DOM unification, `VirtualDOMNode` implements all DOM operations used by `_reconcile_children()` (`appendChild`, `insertBefore`, `remove`), so key-based reconciliation works identically on the server
- [ ] 4.9 Remove environment guard from `_component.py:172` — change `app._defer_depth > 0 and ENVIRONMENT == "pyscript"` to `app._defer_depth > 0`. After virtual DOM unification, both environments run `render()`, and the defer mechanism works correctly on the server via synchronous `schedule_macro_task()`. The guard is an unnecessary optimization that diverges from Decision 3's single-code-path goal

## 5. Remove _render_html() from element subclasses

- [ ] 5.1 Remove `_render_html()` from `TextElement` and `NewLine` in `webcompy/elements/types/_text.py`
- [ ] 5.2 Remove `_render_html()` from `DynamicElement` in `webcompy/elements/types/_dynamic.py`

## 6. Update server-side rendering entry points

- [ ] 6.1 Update SSG generation code to use `ServerDOMPort.render_html(root_node)` instead of calling element `_render_html()` directly
- [ ] 6.2 Update `webcompy/cli/_generate.py` if it references `_render_html()`
- [ ] 6.3 Update `webcompy/cli/_html.py` if it references `_render_html()`

## 7. Element system adapter for server DOMPort

- [ ] 7.1 Verify `DomNodeRef` is compatible with `VirtualDOMNode` — `DomNodeRef.__init_node__(node)` sets `self._node = node` and `node` must satisfy `DOMNode` Protocol; `VirtualDOMNode` already does
- [ ] 7.2 Verify `ElementBase._init_new_node()` works on `VirtualDOMNode` — `setAttribute` and `addEventListener` use `DOMNode` Protocol which `VirtualDOMNode` implements

## 8. Tests

- [ ] 8.1 Write tests for `VirtualDOMNode` — tree construction, attribute operations, event listener recording
- [ ] 8.2 Write tests for `ServerDOMPort.render_html()` — element serialization, void tags, attribute escaping, text escaping, nested trees
- [ ] 8.3 Write tests for unified render path — render the same component tree in both browser mock and server DOMPort, verify identical structure
- [ ] 8.4 Update existing SSG tests — migrate from HTML string comparison to virtual tree structure inspection where beneficial; keep string comparison as integration tests
- [ ] 8.5 Write tests for server-side rendering of components with attributes, event handlers, conditional branches, and list rendering
- [ ] 8.6 Run existing test suite and fix regressions

## 9. E2E test migration to unit tests

### Purely rendering — fully migratable (24 tests)

- [ ] 9.1 Migrate `tests/e2e/test_component.py` (2 tests) — replace `to_be_visible`/`to_have_text` with `TestRenderer.render()` + virtual tree assertions; component text content is fully verifiable via `VirtualDOMNode`
- [ ] 9.2 Migrate `tests/e2e/test_standalone.py` (4 tests) — CDN URL absence, local asset paths, file existence checks; no Playwright usage, move these to `tests/` under `pytest.mark.e2e` removed
- [ ] 9.3 Migrate `tests/e2e/test_bundled_deps.py` (9 tests) — lockfile existence/schema, wheel content, HTML string verification; no Playwright usage, move to `tests/` as regular unit tests
- [ ] 9.4 Migrate `tests/e2e/test_static_site.py` (7 tests) — wheel filename content-hash pattern, zip validity, HTML wheel URL; no Playwright usage, move to `tests/`
- [ ] 9.5 Migrate `test_runtime_local_no_cdn_urls` and `test_runtime_local_static_assets_exist` from `tests/e2e/test_runtime_local.py` (2 tests) — HTML string verification without Playwright

### Mixed — fully migratable with dispatchEvent (29 tests)

- [ ] 9.6 Migrate `test_switch.py` (3 tests) — all tests use only click events; `dispatchEvent(MockDOMEvent("click"))` replaces Playwright `click()`. Default state, toggle on, toggle off all work via virtual DOM assertions.
- [ ] 9.7 Migrate `test_reactive.py` (3 tests) — text update, list operations, dict operations all triggered by button clicks ignoring event arg. dispatchEvent + rerender + virtual tree assertions fully cover.
- [ ] 9.8 Migrate `test_repeat.py` (3 tests) — initial empty state (no interaction) plus add/remove via clicks. dispatchEvent covers all interactive assertions.
- [ ] 9.9 Migrate `test_keyed_repeat.py` (4 of 5 tests) — initial empty, add items, remove first, insert at start all use click-only handlers. **Exclude**: `test_keyed_repeat_input_preserved_after_add` — verifies real browser `<input>` widget state survives keyed reconciliation; virtual DOM has no equivalent widget state.
- [ ] 9.10 Migrate `test_dict_repeat.py` (4 of 5 tests) — same pattern as keyed repeat. **Exclude**: `test_dict_repeat_input_preserved_after_add` — same browser `<input>` widget state requirement.
- [ ] 9.11 Migrate `test_nested_dynamic.py` (6 tests) — all tests (initial view, switch to grid, switch back, add item, add then switch, remove first) use click-only handlers. dispatchEvent + rerender covers all.
- [ ] 9.12 Migrate `test_scoped_style.py` (2 of 7 tests) — `test_scoped_style_attribute_selector` and `test_scoped_style_top_level_media_query` only check `<style>` element `textContent` against virtual DOM. **Exclude**: 5 tests using `getComputedStyle()` which requires a real browser CSS engine.
- [ ] 9.13 Migrate `test_di.py` (2 of 5 tests) — `test_provide_inject_from_parent` and `test_inject_from_app_level` can render DI components directly via TestRenderer with proper DI scope set up. **Exclude**: 3 tests using RouterLink navigation (inert outside PyScript) and `assert_no_console_errors`.
- [ ] 9.14 Migrate `test_lifecycle.py` (2 of 3 tests) — `test_lifecycle_hooks_fire` and `test_on_after_rendering_on_interactions` use click-only handler or no interaction. **Exclude**: `test_on_before_rendering_on_navigation` — depends on RouterLink navigation and RouterView destroy/recreate cycle.

### Verification

- [ ] 9.15 Verify all E2E tests pass after migration — remaining E2E tests must still pass with reduced scope (11 browser-required tests stay in E2E)
- [ ] 9.16 Update CI e2e-matrix in `.github/workflows/ci.yml` if any E2E test files are removed or renamed

## 10. Cleanup

- [ ] 10.1 Search codebase for any remaining `_render_html` references — ensure all are removed or migrated
- [ ] 10.2 Remove any `_render_html`-specific test utilities or helpers
- [ ] 10.3 Update type stubs if `_render_html` appears in any `.pyi` files

## 11. Verification

- [ ] 11.1 Run lint: `uv run ruff check .`
- [ ] 11.2 Run type check: `uv run pyright`
- [ ] 11.3 Run unit tests: `uv run python -m pytest tests/ --tb=short`
- [ ] 11.4 Run SSG and verify output: `uv run python -m webcompy generate --app docs_app.bootstrap:app`
- [ ] 11.5 Diff generated docs against baseline to confirm no output regressions
- [ ] 11.6 Verify dev server starts: `uv run python -m webcompy start --dev --app docs_app.bootstrap:app`
