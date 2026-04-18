## 1. Rename test app package

- [x] 1.1 Rename `tests/e2e/app/` directory to `tests/e2e/my_app/`
- [x] 1.2 Update `tests/e2e/webcompy_config.py` to point to `my_app` instead of `app`
- [x] 1.3 Update `tests/e2e/test_static_site.py` to reference `my_app` instead of `app`

## 2. Add parametrized fixtures to conftest.py

- [x] 2.1 Move `static_site` and `static_server` fixtures from `test_static_site.py` into `conftest.py` (session-scoped)
- [x] 2.2 Create a parametrized `serving_mode` fixture with values `["dev", "static"]`
- [x] 2.3 Refactor `app_page` fixture to be function-scoped, parametrized by `serving_mode`, navigating to the dev-server URL or static-site URL accordingly
- [x] 2.4 Refactor `page_on` fixture to be function-scoped, parametrized by `serving_mode`, returning a callable that navigates to the appropriate URL

## 3. Add console error detection

- [x] 3.1 Create a `console_errors` fixture that registers a `page.on("console", ...)` listener to capture console messages during the test
- [x] 3.2 Create a `assert_no_python_errors` fixture that checks collected console messages for Python tracebacks after PyScript initialization completes

## 4. Update existing test files for parametrization

- [x] 4.1 Update `test_bootstrap.py` to use the parametrized `app_page` fixture and add `assert_no_python_errors` assertion
- [x] 4.2 Update `test_reactive.py` to use the parametrized `page_on` fixture (no changes needed — same fixture name)
- [x] 4.3 Update `test_event.py` to use the parametrized `page_on` fixture (no changes needed)
- [x] 4.4 Update `test_router.py` to use the parametrized `app_page` and `page_on` fixtures (no changes needed)
- [x] 4.5 Update remaining test files (no changes needed — same fixture names)

## 5. Refactor test_static_site.py

- [x] 5.1 Move wheel-related assertions (filename matches HTML, valid zip) to remain in `test_static_site.py` as non-parametrized tests
- [x] 5.2 Remove the `test_app_loads_in_browser` test from `test_static_site.py` (subsumed by parametrized `test_app_loads` in `test_bootstrap.py`)

## 6. Verify and clean up

- [x] 6.1 Run `uv run python -m pytest tests/ -x -q --ignore=tests/e2e` to confirm unit tests still pass
- [x] 6.2 Run `uv run ruff check .` and `uv run pyright` to confirm lint and type-check pass