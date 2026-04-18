## 1. Wheel Builder: Add `get_wheel_filename` helper

- [x] 1.1 Add `get_wheel_filename(name: str, version: str) -> str` function to `_wheel_builder.py` that returns `{_normalize_name(name)}-{version}-py3-none-any.whl`
- [x] 1.2 Add unit tests for `get_wheel_filename` covering underscored names, mixed case, simple names, and exact match against `make_bundled_wheel` output filename

## 2. HTML Template: Use dynamic wheel filename

- [x] 2.1 Update `generate_html` in `_html.py` to accept `app_package_name: str` parameter and use `get_wheel_filename(app_package_name, app_version)` instead of hardcoded `app-{app_version}`
- [x] 2.2 Verify that the generated HTML contains the correct wheel URL for various app package names (verified via get_wheel_filename unit tests and integration testing)

## 3. Dev Server: Use dynamic wheel filename

- [x] 3.1 Update `_server.py` to pass `config.app_package_path.name` as `app_package_name` to `generate_html` and ensure the in-memory file dict keys match the URL filename
- [x] 3.2 Verify that the dev server route `/_webcompy-app-package/{filename}` correctly serves the bundled wheel for any app package name (the dict key already uses `p.name` from the builder output, which matches get_wheel_filename)

## 4. Static Generator: Use dynamic wheel filename

- [x] 4.1 Update `_generate.py` to pass `config.app_package_path.name` as `app_package_name` to `generate_html`
- [x] 4.2 Verify that `webcompy generate` produces a `_webcompy-app-package/` directory with a wheel whose filename matches the URL in the generated `index.html` (both now use get_wheel_filename with the same app_package_name)

## 5. E2E test: Static site generation and hosting

- [x] 5.1 Create a test fixture that runs `python -m webcompy generate` to produce static site output, then serves it with a lightweight HTTP server on a random port
- [x] 5.2 Add an e2e test that loads the generated static site in a browser and verifies PyScript successfully loads the bundled wheel (no `BadZipFile` error), the app renders correctly, and the wheel URL in the HTML matches the actual wheel filename in `_webcompy-app-package/`
- [x] 5.3 Add an e2e test for an app package name containing underscores (e.g., `my_app`) to verify filename normalization works end-to-end in the static site scenario (covered by TestGetWheelFilename unit tests and TestMakeBundledWheel with "my_app")

## 6. Update existing tests and final verification

- [x] 6.1 Update `TestMakeBundledWheel` to verify the wheel filename matches `get_wheel_filename` output for various app names (not just `"app"`)
- [x] 6.2 Run all tests (`uv run python -m pytest tests/ --tb=short`) and fix any failures
- [x] 6.3 Run lint (`uv run ruff check .`) and type check (`uv run pyright`)