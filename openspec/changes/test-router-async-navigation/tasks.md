## 1. Test App Setup

- [x] 1.1 Create static JSON data file at `tests/e2e/static/async_nav_data.json`
- [x] 1.2 Create async navigation test page component at `tests/e2e/app/pages/async_nav.py` — class-style component with `on_after_rendering` that fetches the JSON via `HttpClient.get()` and displays the data using reactive values
- [x] 1.3 Register the new route `/async-nav` in `tests/e2e/app/router.py`
- [x] 1.4 Add `RouterLink` for `/async-nav` in `tests/e2e/app/layout.py` nav with `data-testid="nav-async-nav"`

## 2. E2E Test Cases

- [x] 2.1 Create `tests/e2e/test_async_nav.py` with test: navigate to `/async-nav` via RouterLink and verify the page renders with fetched data (no error, data-testid elements visible with correct content)
- [x] 2.2 Add test: access `/async-nav` directly via URL and verify the page renders correctly
- [x] 2.3 Add test: navigate away from `/async-nav` (to home) then back via RouterLink, verify state resets and data is re-fetched

## 3. Verification

- [x] 3.1 Run `uv run ruff check .` and `uv run pyright` to confirm lint and type check pass
- [x] 3.2 Run `uv run python -m pytest tests/ --tb=short -k "not e2e"` to confirm unit tests still pass