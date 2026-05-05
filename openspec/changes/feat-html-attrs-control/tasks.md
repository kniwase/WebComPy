- [ ] **Task 1**: Add `set_html_attr` and `remove_html_attr` to `AppDocumentRoot`
  - Add `_html_attrs: dict[str, str | Computed[str]]` field to `AppDocumentRoot`
  - Implement `set_html_attr(key, value)` and `remove_html_attr(key)` methods
  - Add `html_attrs` property that resolves `Computed` values for SSG
  - Estimated: 30 min

- [ ] **Task 2**: Forward new methods via `WebComPyApp` properties
  - Add `set_html_attr` and `remove_html_attr` properties to `WebComPyApp`
  - Follow existing pattern (`set_title`, `append_script`, etc.)
  - Estimated: 15 min

- [ ] **Task 3**: Update SSG HTML generation in `generate_html()`
  - Pass `app._root.html_attrs` into the `<html>` `_HtmlElement` constructor
  - Ensure `Computed` values are resolved to strings at render time
  - Estimated: 15 min

- [ ] **Task 4**: Implement browser-side DOM synchronization
  - In `AppDocumentRoot._render()`, sync `_html_attrs` to `browser.document.documentElement`
  - Handle both initial render and subsequent reactive updates
  - Use `browser.document.documentElement.setAttribute()` / `removeAttribute()`
  - Estimated: 30 min

- [ ] **Task 5**: Add unit tests
  - Test `set_html_attr` / `remove_html_attr` on `AppDocumentRoot` (SSG context)
  - Test HTML output contains correct attributes
  - Test `WebComPyApp` property forwarding
  - Estimated: 30 min

- [ ] **Task 6**: Run lint, typecheck, and tests
  - `uv run ruff check .`
  - `uv run pyright`
  - `uv run python -m pytest tests/ --tb=short`
  - Estimated: 15 min
