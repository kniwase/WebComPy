- [x] **Task 1**: Add `set_html_attr` and `remove_html_attr` to `AppDocumentRoot`
  - Add `_html_attrs: dict[str, str | Computed[str]]` field to `AppDocumentRoot`
  - Implement `set_html_attr(key, value)` and `remove_html_attr(key)` methods
  - Add `html_attrs` property that resolves `Computed` values for SSG
  - **For `Computed` values**: store the `Computed` instance directly (not its `.value`)
  - Estimated: 30 min

- [x] **Task 2**: Forward new methods via `WebComPyApp` properties
  - Add `set_html_attr` and `remove_html_attr` properties to `WebComPyApp`
  - Follow existing pattern (`set_title`, `append_script`, etc.)
  - Estimated: 15 min

- [x] **Task 3**: Update SSG HTML generation in `generate_html()`
  - Pass `app._root.html_attrs` into the `<html>` `_HtmlElement` constructor
  - Ensure `Computed` values are resolved to strings at render time
  - Estimated: 15 min

- [x] **Task 4**: Implement browser-side DOM synchronization with reactive updates
  - In `AppDocumentRoot.__init__()`, register `on_after_updating` callbacks for each `Computed` html attr
  - Callbacks SHALL use `browser.document.documentElement.setAttribute()` / `removeAttribute()`
  - In `AppDocumentRoot._render()`, perform initial sync of all attributes to the DOM
  - When `remove_html_attr` is called, remove the callback registration if it was a `Computed` value
  - Handle the case where `browser` is `None` (server-side rendering context)
  - Estimated: 45 min

- [x] **Task 5**: Add unit tests
  - Test `set_html_attr` / `remove_html_attr` on `AppDocumentRoot` (SSG context)
  - Test HTML output contains correct attributes
  - Test `WebComPyApp` property forwarding
  - Test reactive `Computed` attribute updates trigger DOM changes
  - Estimated: 45 min

- [x] **Task 6**: Run lint, typecheck, and tests
  - `uv run ruff check .` ✅ PASS
  - `uv run pyright` ✅ PASS
  - `uv run python -m pytest tests/test_app_instance.py` ✅ 30/30 PASS
