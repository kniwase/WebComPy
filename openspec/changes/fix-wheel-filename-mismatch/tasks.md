## 1. Wheel Builder: Add `get_wheel_filename` helper

- [ ] 1.1 Add `get_wheel_filename(name: str, version: str) -> str` function to `_wheel_builder.py` that returns `{_normalize_name(name)}-{version}-py3-none-any.whl`
- [ ] 1.2 Add unit tests for `get_wheel_filename` covering underscored names, mixed case, simple names, and exact match against `make_bundled_wheel` output filename

## 2. HTML Template: Use dynamic wheel filename

- [ ] 2.1 Update `generate_html` in `_html.py` to accept `app_package_name: str` parameter and use `get_wheel_filename(app_package_name, app_version)` instead of hardcoded `app-{app_version}`
- [ ] 2.2 Add test or manually verify that the generated HTML contains the correct wheel URL for various app package names

## 3. Dev Server: Use dynamic wheel filename

- [ ] 3.1 Update `_server.py` to pass `config.app_package_path.name` as `app_package_name` to `generate_html` and ensure the in-memory file dict keys match the URL filename
- [ ] 3.2 Verify that the dev server route `/_webcompy-app-package/{filename}` correctly serves the bundled wheel for any app package name

## 4. Static Generator: Use dynamic wheel filename

- [ ] 4.1 Update `_generate.py` to pass `config.app_package_path.name` as `app_package_name` to `generate_html`
- [ ] 4.2 Verify that `webcompy generate` produces a `_webcompy-app-package/` directory with a wheel whose filename matches the URL in the generated `index.html`

## 5. E2E test: Static site generation and hosting

- [ ] 5.1 Create a test fixture that runs `python -m webcompy generate` to produce static site output, then serves it with a lightweight HTTP server (e.g., `python -m http.server` or Starlette static files) on a random port
- [ ] 5.2 Add an e2e test that loads the generated static site in a browser and verifies PyScript successfully loads the bundled wheel (no `BadZipFile` error), the app renders correctly, and the wheel URL in the HTML matches the actual wheel filename in `_webcompy-app-package/`
- [ ] 5.3 Add an e2e test for an app package name containing underscores (e.g., `my_app`) to verify filename normalization works end-to-end in the static site scenario

## 6. Update existing tests and final verification

- [ ] 6.1 Update `TestMakeBundledWheel` to verify the wheel filename matches `get_wheel_filename` output for various app names (not just `"app"`)
- [ ] 6.2 Run all tests (`uv run python -m pytest tests/ --tb=short`) and fix any failures
- [ ] 6.3 Run lint (`uv run ruff check .`) and type check (`uv run pyright`)