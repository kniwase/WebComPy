## 1. ComponentGenerator: expose cid and scoped_style

- [x] 1.1 Add `_id` property to `ComponentGenerator` (read-only accessor for external use)
- [x] 1.2 Verify `scoped_style` getter returns correctly scoped CSS string for all selector types (combinator, at-rule, pseudo, nested)

## 2. AppDocumentRoot: replace monolithic style with per-component reconciliation

- [x] 2.1 Remove `AppDocumentRoot.style` property (concatenated CSS string)
- [x] 2.2 Add `AppDocumentRoot.scoped_styles` property returning `dict[str, str]` (cid → CSS), sorted by cid, excluding empty styles
- [x] 2.3 Add `AppDocumentRoot._reconcile_scoped_styles()` method:
  - ENVIRONMENT guard: return immediately if not pyscript
  - Inject `*[hidden]{display:none}` rule as `<style id="webcompy-scoped-styles">` if not present
  - Iterate `ComponentStore.components`, for each with non-empty `scoped_style`, check `querySelector('style[data-webcompy-cid="{cid}"]')`, inject missing
- [x] 2.4 Replace `self.__loading`-guarded scoped style injection block in `_render()` with call to `_reconcile_scoped_styles()`
- [x] 2.5 Verify `__loading` guard removal does not affect loading screen removal logic

## 3. AppDocumentRoot: expose scoped_styles (replacing style)

- [x] 3.1 Remove `AppDocumentRoot.style` property (concatenated CSS string)
- [x] 3.2 Add `AppDocumentRoot.scoped_styles` property returning `dict[str, str]` (cid → CSS), sorted by cid, excluding empty styles
- [x] 3.3 Add `WebComPyApp.scoped_styles` forwarding property; update SSG `_html.py` to use `app.scoped_styles` instead of `app.style`; remove `WebComPyApp.style` forwarding property

## 4. SSG: per-component `<style>` generation

- [x] 4.1 Update `_html.py` `generate_html()` to render `ctx.scoped_styles` dict as per-component `<style data-webcompy-cid="...">` elements
- [x] 4.2 Keep `<style id="webcompy-scoped-styles">*[hidden]{display:none}</style>` as a standalone element
- [x] 4.3 Remove old monolithic style element construction

## 5. SSG: pre-resolve lazy routes

- [x] 5.1 In `_generate.py` `generate_static_site()`, add pre-resolve loop before per-route generation:
  - For each route entry, if page component is `LazyComponentGenerator` (has `_preload` attr), call `_preload()`
- [x] 5.2 Verify pre-resolve does not break path parameter generation for routes with `path_params`

## 6. HeadElement VDOM class

- [x] 6.1 Create `webcompy/elements/_head.py` with `HeadElement` class extending `ElementWithChildren`
- [x] 6.2 `HeadElement.__init__` accepts `HeadPropsStore`, constructs initial state
- [x] 6.3 Implement `_render()` for browser: reconcile scoped CSS styles into document head (inject `*[hidden]` base rule, per-component style elements), idempotent via `data-webcompy-cid` attribute checks
- [x] 6.4 Implement `get_link_elements_html()` and `get_script_elements_html()` for server-side rendering
- [x] 6.5 Integrate `_reconcile_scoped_styles()` logic into `HeadElement._render()`; **remove `_reconcile_scoped_styles()` from `AppDocumentRoot`** (this is the final home, not a second copy)
- [x] 6.6 Handle `html_attrs` management on `HeadElement` (`set_html_attr`, `remove_html_attr`, `get_html_attrs`)
- [x] 6.7 Export `HeadElement` from `webcompy/elements/__init__.py`

## 7. AppDocumentRoot: delegate head management to HeadElement

- [x] 7.1 Initialize `HeadElement` in `AppDocumentRoot.__init__`, passing `HeadPropsStore`
- [x] 7.2 Delegate `_reconcile_html_attrs()` and `_reconcile_scoped_styles()` calls to `HeadElement` in `_render()`
- [x] 7.3 Keep existing consumer-facing API working (e.g., `app.set_head()`, `app.set_title()`) through delegation

## 8. SSG _html.py: use scoped_styles dict for CSS generation

- [x] 8.1 Update `generate_html()` to iterate `app.scoped_styles` dict for per-component `<style>` elements
- [x] 8.2 Plugin head scripts stay in `_html.py` (not managed by HeadElement)
- [x] 8.3 Keep core CSS and PyScript bootstrapping in `_html.py` (these are not component-managed)

## 9. Merge origin/main (#171 testing module)

- [ ] 9.1 Execute `git merge origin/main`
- [ ] 9.2 Resolve conflicts in `_generator.py` — keep `_cid` attribute + `_id` property (our change)
- [ ] 9.3 Resolve conflicts in `_lazy.py` — keep `_cid` attribute accesses (our change)
- [ ] 9.4 Resolve conflicts in `_root_component.py` — keep `scoped_styles` dict + HeadElement integration (our change)
- [ ] 9.5 Resolve conflicts in `_app.py` — keep `scoped_styles` forwarding (our change)
- [ ] 9.6 Resolve conflicts in `_head.py` — keep the file (our change), testing module deleted it
- [ ] 9.7 Resolve conflicts in `__init__.py` — keep `HeadElement` export (our change)
- [ ] 9.8 Resolve conflicts in `_html.py` — keep per-component style generation (our change)
- [ ] 9.9 Resolve conflicts in `_generate.py` — keep pre-resolve loop (our change)
- [ ] 9.10 Resolve conflicts in `test_app_instance.py` — keep `scoped_styles` assertion (our change)
- [ ] 9.11 Resolve conflicts in `AGENTS.md` — merge both spec mappings (our specs + testing-module)
- [ ] 9.12 Verify all new files from #171 are present: `webcompy/testing/*`, new test files, etc.

## 10. Extend FakeBrowserDOMPort with ServerDOMPort base and document tree

- [ ] 10.1 Change `FakeBrowserDOMPort` to extend `ServerDOMPort` instead of `DOMPort(ABC)`
- [ ] 10.2 Add `__init__` that creates internal document tree: `_html`, `_head`, `_body` as FakeDOMNode instances
- [ ] 10.3 Override `create_element(tag)` to return `FakeDOMNode(tag)` (ServerDOMPort returns VirtualDOMNode)
- [ ] 10.4 Implement `query_selector(selector)` — simple tag-name DFS search on `_html` tree
- [ ] 10.5 Implement `get_element_by_id(element_id)` — DFS search by `id` attribute on `_html` tree
- [ ] 10.6 Inherit all other methods from `ServerDOMPort` (create_event, create_text_node, set_title, add_document_event_listener, render_html)
- [ ] 10.7 Update `TestRenderer.render()` to use extended FakeBrowserDOMPort (it already wires it, verify no breakage)

## 11. New tests using testing module

- [ ] 11.1 **SSG integration test**: Create a page component with scoped CSS, use `create_test_asgi_app()` + `httpx` to verify `<style data-webcompy-cid="...">` elements appear in HTML output and `*[hidden]{display:none}` is present
- [ ] 11.2 **SSG lazy route test**: Pre-resolved lazy route component's scoped CSS appears in every page's HTML
- [ ] 11.3 **HeadElement browser-path test**: Verify `HeadElement._render()` injects `*[hidden]` base rule via FakeBrowserDOMPort tree
- [ ] 11.4 **HeadElement component style injection test**: Verify per-component `<style>` elements are appended to `head` node when component has scoped CSS
- [ ] 11.5 **HeadElement idempotent test**: Verify second `_render()` call does not create duplicate `<style>` elements
- [ ] 11.6 **HeadElement no-duplicate on existing styles test**: Verify pre-existing `data-webcompy-cid` elements in document tree are not duplicated

## 12. CI review agent update

- [ ] 12.1 Add `testing-module` to file→spec mapping in `.opencode/agents/ci-review.md` under `webcompy/testing/`
- [ ] 12.2 Update `AGENTS.md` file→spec mapping: add both branches' entries (scoped-css-incremental, head-vdom, testing-module)

## 13. Final verification

- [ ] 13.1 Run `uv run ruff check .` — no errors
- [ ] 13.2 Run `uv run ruff format .` — all formatted
- [ ] 13.3 Run `uv run pyright` — 0 errors
- [ ] 13.4 Run `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs` — all pass
- [ ] 13.5 Run SSG: `uv run python -m webcompy generate --config docs_app.webcompy_config` — per-component style elements confirmed
