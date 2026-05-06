# Tasks: Split Mode — Two-Wheel Split for Browser Cache Optimization

**Strategy**: Two wheels (framework + app-with-deps) in `py-config.packages`.

- [x] **Task 0: Experiment** — determine viable loading strategy
- [x] **Task 1: Add `wheel_mode` to AppConfig**
- [x] **Task 2: Add `--wheel-mode` CLI flag**
- [x] **Task 3: Reintroduce `make_browser_webcompy_wheel()`**
- [x] **Task 4: Update `make_webcompy_app_package()` for split mode**
- [x] **Task 5: Update dev server for two-wheel serving**
- [x] **Task 6: Update SSG for two-wheel output**
- [x] **Task 7: Update HTML generation for split mode**
- [x] **Task 8: Update E2E tests for two-wheel split mode**
  - `conftest.py`: split_static_site fixture expects exactly 2 wheels
  - `test_static_site.py`: verify both wheels have content-hash, both in HTML
- [x] **Task 9: Lint, typecheck, and test validation**
  - `uv run ruff check .`
  - `uv run pyright`
  - `uv run python -m pytest tests/ --tb=short`
  - docs_app E2E tests
