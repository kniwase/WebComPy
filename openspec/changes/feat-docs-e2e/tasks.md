## 1. Test Infrastructure

- [ ] 1.1 Create `tests/e2e_docs/conftest.py` with fixtures: `docs_prod_server`, `docs_static_site`, `docs_static_server`, `docs_server_url`, `docs_app_page`, `docs_page_on`, `console_errors`, `assert_no_python_errors`, and `pytest_generate_tests` for `--serving-mode`
- [ ] 1.2 Configure `PYSCRIPT_INIT_TIMEOUT = 300_000` for docs_app tests
- [ ] 1.3 Set up `docs_prod_server` fixture to start `webcompy start --app docs_app.bootstrap:app --port 8081`
- [ ] 1.4 Set up `docs_static_site` fixture to run `webcompy generate --app docs_app.bootstrap:app --dist .tmp/e2e-docs-static/dist`

## 2. Page Test Files

- [ ] 2.1 Create `tests/e2e_docs/test_home.py` — load `/`, verify "What is WebComPy" heading, no console errors, page title
- [ ] 2.2 Create `tests/e2e_docs/test_documents.py` — load `/documents`, verify "Work In Progress" text, no console errors
- [ ] 2.3 Create `tests/e2e_docs/test_helloworld.py` — load `/sample/helloworld`, verify "HelloWorld" heading, "Hello WebComPy!" text, no console errors
- [ ] 2.4 Create `tests/e2e_docs/test_fizzbuzz.py` — load page, verify initial state (Count: 10, list items), test Add/Pop/Hide buttons, no console errors
- [ ] 2.5 Create `tests/e2e_docs/test_todo.py` — load page, verify initial items, test Add ToDo and Remove Done Items, no console errors
- [ ] 2.6 Create `tests/e2e_docs/test_matplotlib.py` — load page (extended timeout), verify "Square Wave" heading, "Value: 15" initial state, test "+" button increments value, verify img exists, no console errors
- [ ] 2.7 Create `tests/e2e_docs/test_fetch.py` — skip marker with reason about missing sample.json, to be enabled after feat-docs-app-rename

## 3. CI Integration

- [ ] 3.1 Add `docs-home`, `docs-demos`, `docs-matplotlib`, `docs-fetch` groups to `e2e-matrix` in `.github/workflows/ci.yml`
- [ ] 3.2 Verify CI runs all docs E2E test groups with both `prod` and `static` serving modes

## 4. Verify

- [ ] 4.1 Run `uv run python -m pytest tests/e2e_docs/ --tb=short` locally and verify all tests pass (excluding skipped fetch)
- [ ] 4.2 Run `uv run ruff check .` and verify no lint errors in new test files
- [ ] 4.3 Run `uv run python -m pytest tests/ --tb=short` and verify existing tests still pass