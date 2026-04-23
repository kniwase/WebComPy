## 1. Refactor _Loadscreen markup and styles

- [x] 1.1 Update `_Loadscreen.__init__` to remove the intermediate `<div class="container">` wrapper; make `#webcompy-loading` the direct parent of the spinner
- [x] 1.2 Rename `.loader` to `.wc-loader` in `_style` and in the DOM generator
- [x] 1.3 Remove the `body` CSS selector from `_style`; add `position: fixed`, `inset: 0`, `display: flex`, `align-items: center`, `justify-content: center`, `background`, and `z-index` directly to the `#webcompy-loading` selector

## 2. Verify generated HTML correctness

- [x] 2.1 Run a Python script to call `_Loadscreen().render_html()` and assert that the output no longer contains `class="container"`, no longer contains `body{`, and still contains `#webcompy-loading` and `.wc-loader`
- [x] 2.2 Visually inspect the rendered inline style string to confirm it is valid CSS (no missing braces, correct selector nesting)

## 3. Run existing tests to prevent regression

- [x] 3.1 Run `uv run python -m pytest tests/ --tb=short` and confirm all tests pass
- [x] 3.2 Confirm E2E tests that check `#webcompy-loading` still pass (no selector breakage)

## 4. Lint and format

- [x] 4.1 Run `uv run ruff check webcompy/cli/_html.py` — should report no issues
- [x] 4.2 Run `uv run ruff format webcompy/cli/_html.py`
