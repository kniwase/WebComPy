## 1. Test Infrastructure

- [x] 1.1 Create `tests/e2e_docs/conftest.py` with server fixtures: `docs_prod_server` (port 8081, `docs_app.bootstrap:app`), `docs_static_site` (generate to `.tmp/e2e-docs-static/dist`), `docs_static_server`, `docs_server_url`, `pytest_generate_tests` for `--serving-mode`, and `PYSCRIPT_INIT_TIMEOUT = 300_000`
- [x] 1.2 Add navigation and page fixtures to conftest: `docs_app_page` (navigates to root, waits for PyScript init, keeps page loaded) and `docs_page_on` (returns callable that navigates to a given path and waits for init)
- [x] 1.3 Add assertion fixtures to conftest: `console_errors` (collects browser console error messages) and `assert_no_python_errors` (asserts no Python tracebacks after test execution)

## 2. Page Test Files

- [x] 2.1 Create `tests/e2e_docs/test_home.py` — load `/`, verify "What is WebComPy" heading, no console errors, page title, SPA navigation to HelloWorld and back
- [x] 2.2 Create `tests/e2e_docs/test_documents.py` — load `/documents`, verify "Work In Progress" text, no console errors
- [x] 2.3 Create `tests/e2e_docs/test_helloworld.py` — load `/sample/helloworld`, verify "HelloWorld" heading, "Hello WebComPy!" text, no console errors
- [x] 2.4 Create `tests/e2e_docs/test_fizzbuzz.py` — load page, verify initial state (Count: 10, list items), test Add/Pop/Hide buttons, no console errors
- [x] 2.5 Create `tests/e2e_docs/test_todo.py` — load page, verify initial items, test Add ToDo and Remove Done Items, no console errors
- [x] 2.6 Create `tests/e2e_docs/test_matplotlib.py` — load page (extended timeout), verify "Square Wave" heading, "Value: 15" initial state, test "+" button increments value, verify img exists, no console errors
- [x] 2.7 Create `tests/e2e_docs/test_fetch.py` — skip marker with reason about missing sample.json, to be enabled after feat-docs-app-rename

## 3. CI Integration

- [x] 3.1 Add `docs-home`, `docs-demos`, `docs-matplotlib`, `docs-fetch` groups to `e2e-matrix` in `.github/workflows/ci.yml`
- [x] 3.2 Verify CI runs all docs E2E test groups with both `prod` and `static` serving modes

## 4. Verify

- [x] 4.1 Run `uv run python -m pytest tests/e2e_docs/ --tb=short` locally and verify all tests pass (excluding skipped fetch)
- [x] 4.2 Run `uv run ruff check .` and verify no lint errors in new test files
- [x] 4.3 Run `uv run python -m pytest tests/ --tb=short` and verify existing tests still pass
