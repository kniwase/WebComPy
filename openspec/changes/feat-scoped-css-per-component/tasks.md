## 1. ComponentGenerator: expose cid and scoped_style

- [ ] 1.1 Add `_id` property to `ComponentGenerator` (read-only accessor for external use)
- [ ] 1.2 Verify `scoped_style` getter returns correctly scoped CSS string for all selector types (combinator, at-rule, pseudo, nested)

## 2. AppDocumentRoot: replace monolithic style with per-component reconciliation

- [ ] 2.1 Remove `AppDocumentRoot.style` property (concatenated CSS string)
- [ ] 2.2 Add `AppDocumentRoot.scoped_styles` property returning `dict[str, str]` (cid → CSS), sorted by cid, excluding empty styles
- [ ] 2.3 Add `AppDocumentRoot._reconcile_scoped_styles()` method:
  - ENVIRONMENT guard: return immediately if not pyscript
  - Inject `*[hidden]{display:none}` rule as `<style id="webcompy-scoped-styles">` if not present
  - Iterate `ComponentStore.components`, for each with non-empty `scoped_style`, check `querySelector('style[data-webcompy-cid="{cid}"]')`, inject missing
- [ ] 2.4 Replace `self.__loading`-guarded scoped style injection block in `_render()` with call to `_reconcile_scoped_styles()`
- [ ] 2.5 Verify `__loading` guard removal does not affect loading screen removal logic

## 3. RenderContext: expose scoped_styles

- [ ] 3.1 Remove `RenderContext.style` property
- [ ] 3.2 Add `RenderContext.scoped_styles` property delegating to `self._root.scoped_styles`, with `_check_disposed()` guard
- [ ] 3.3 Update any internal references from `ctx.style` to `ctx.scoped_styles`

## 4. SSG: per-component `<style>` generation

- [ ] 4.1 Update `_html.py` `generate_html()` to render `ctx.scoped_styles` dict as per-component `<style data-webcompy-cid="...">` elements
- [ ] 4.2 Keep `<style id="webcompy-scoped-styles">*[hidden]{display:none}</style>` as a standalone element
- [ ] 4.3 Remove old monolithic style element construction

## 5. SSG: pre-resolve lazy routes

- [ ] 5.1 In `_generate.py` `generate_static_site()`, add pre-resolve loop before per-route generation:
  - For each route entry, if page component is `LazyComponentGenerator` (has `_preload` attr), call `_preload()`
- [ ] 5.2 Verify pre-resolve does not break path parameter generation for routes with `path_params`

## 6. HeadElement VDOM class

- [ ] 6.1 Create `webcompy/elements/_head.py` with `HeadElement` class extending `ElementWithChildren`
- [ ] 6.2 `HeadElement.__init__` accepts `HeadPropsStore`, constructs initial children: `TitleElement`, `MetaElement`, `LinkElement`, `ScriptElement`, `StyleElement` subclasses or generic `Element` wrappers
- [ ] 6.3 Implement `_render()` for browser: reconcile VDOM children with actual `<head>` DOM (create/update/remove child elements)
- [ ] 6.4 Implement `render_html()` for server: produce HTML string for `<head>` and all children
- [ ] 6.5 Integrate `_reconcile_scoped_styles()` logic into `HeadElement` as style children management; **remove `_reconcile_scoped_styles()` from `AppDocumentRoot`** (this is the final home, not a second copy)
- [ ] 6.6 Handle `html_attrs` management as part of `HeadElement` (since `<html>` is the sibling container)
- [ ] 6.7 Export `HeadElement` from `webcompy/elements/__init__.py`

## 7. AppDocumentRoot: delegate head management to HeadElement

- [ ] 7.1 Initialize `HeadElement` in `AppDocumentRoot.__init__`, passing `HeadPropsStore`
- [ ] 7.2 Deprecate imperative methods (`set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`): delegate to `HeadElement`
- [ ] 7.3 Deprecate `head`, `scripts` properties: delegate to `HeadElement`
- [ ] 7.4 Keep existing consumer-facing API working (e.g., `app.set_head()`, `app.set_title()`) through delegation

## 8. SSG _html.py: use HeadElement for head rendering

- [ ] 8.1 Update `generate_html()` to use `HeadElement.render_html()` for `<head>` generation instead of manual `_HtmlElement` construction
- [ ] 8.2 Plugin head scripts integration: decide whether to pass to `HeadElement` or keep in `_html.py`
- [ ] 8.3 Keep core CSS and PyScript bootstrapping in `_html.py` (these are not component-managed)

## 9. Test updates

- [ ] 9.1 Update `tests/test_elements_browser.py` scoped style tests: assert per-component `data-webcompy-cid` elements
- [ ] 9.2 Update `tests/test_html_generation.py`: assert `data-webcompy-cid` style elements in SSG output
- [ ] 9.3 Update `tests/test_components.py` style-related assertions
- [ ] 9.4 Update `tests/test_server_rendering.py` style assertions
- [ ] 9.5 Update `tests/test_full_hydration.py` hydration style checks
- [ ] 9.6 Add test: lazy component styles injected after navigation
- [ ] 9.7 Add test: SSG pre-resolve includes all lazy component styles in every page
- [ ] 9.8 Add test: `_reconcile_scoped_styles` idempotent (no duplicates on repeated calls)
- [ ] 9.9 Add test: `HeadElement` renders correct HTML in server mode
- [ ] 9.10 Add test: `HeadElement` updates DOM in browser mode

## 10. CI review agent update

- [ ] 10.1 Update `.opencode/agents/ci-review.md` file→spec mapping: add `scoped-css-incremental`, `head-vdom` entries
- [ ] 10.2 Update `AGENTS.md` file→spec mapping table accordingly

## 11. Verification

- [ ] 11.1 Run `uv run ruff check .` — no errors
- [ ] 11.2 Run `uv run ruff format .` — all formatted
- [ ] 11.3 Run `uv run pyright` — 0 errors (no new errors beyond pre-existing)
- [ ] 11.4 Run `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs` — all pass
- [ ] 11.5 Run SSG: `uv run python -m webcompy generate --app docs_app.bootstrap:app` and verify output
- [ ] 11.6 Verify dev server: `uv run python -m webcompy start --dev --app docs_app.bootstrap:app` loads correctly
