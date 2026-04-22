# Tasks: Wheel Split — Browser-Only Wheel, Dependency Bundling, and Browser Cache Strategy

- [ ] **Task 1: Implement `make_browser_webcompy_wheel()`**

**Estimated time: ~1 hour**

### Steps

1. Open `webcompy/cli/_wheel_builder.py`.
2. Add `_BROWSER_ONLY_EXCLUDE = {"cli"}` constant.
3. Implement `make_browser_webcompy_wheel(webcompy_package_dir, dest, version)`:
   - Walk `webcompy/` directory recursively.
   - Skip any subdirectory whose relative path contains a part in `_BROWSER_ONLY_EXCLUDE`.
   - Include `.py`, `.pyi`, `py.typed`, `__init__.py`, `_version.py`, and other standard files.
   - Call the existing `_make_wheel()` (or equivalent internal function) with `name="webcompy"`.
4. Add helper `get_webcompy_package_dir()` that returns the absolute `pathlib.Path` to the `webcompy/` package.
5. Write a unit test: `test_browser_wheel_excludes_cli` that calls `make_browser_webcompy_wheel()`, extracts the ZIP, and asserts that no path contains `cli/`.

### Acceptance Criteria

- `make_browser_webcompy_wheel()` produces a `.whl` file.
- Extracting the wheel shows `webcompy/` directory with `app/`, `elements/`, `reactive/`, etc.
- No `webcompy/cli/` directory exists in the extracted wheel.
- Unit test passes.

---

- [ ] **Task 2: Update `make_webcompy_app_package()` for `bundled_deps`**

**Estimated time: ~0.5 hours**

### Steps

1. Modify `make_webcompy_app_package()` signature to accept `bundled_deps: list[tuple[str, pathlib.Path]] | None = None`.
2. Pass `package_dirs` to `make_bundled_wheel()` including all bundled dependency directories.
3. Test that `bundled_deps` packages appear in `top_level.txt`.

### Acceptance Criteria

- `make_webcompy_app_package()` with `bundled_deps=[("mypackage", path)]` produces a wheel containing the `mypackage/` directory.
- `top_level.txt` lists both the app package and `mypackage`.

---

- [ ] **Task 3: Implement `_discover_dependency_package_dirs()`**

**Estimated time: ~0.5 hours**

### Steps

1. Add `_discover_dependency_package_dirs()` to `_wheel_builder.py`.
2. For each dependency:
   - Try `importlib.util.find_spec(dep)`.
   - If successful and `spec.origin` exists, treat as pure-Python and add to `bundled`.
   - If `spec.origin` is None or `find_spec` fails, treat as C-extension/built-in and add to `pyodide_builtin`.
3. Write a unit test.

### Acceptance Criteria

- Pure-Python packages are discovered as `bundled`.
- C-extension / unknown packages are listed as `pyodide_builtin`.
- Tests cover both cases.

---

- [ ] **Task 4: Update `create_asgi_app()` to serve two wheels with cache headers**

**Estimated time: ~1 hour**

### Steps

1. In `webcompy/cli/server.py` (or wherever `create_asgi_app` is defined):
   - Build both wheels at startup.
   - Map stable URLs to wheel file contents.
2. Set `Cache-Control` headers for wheel routes:
   - Framework wheel: `max-age=86400, must-revalidate`
   - App wheel: `no-cache` (dev mode)
3. Ensure `Content-Type: application/zip` is set.
4. Write a unit test.

### Acceptance Criteria

- `GET /_webcompy-app-package/webcompy-py3-none-any.whl` returns 200.
- `GET /_webcompy-app-package/{app_name}-py3-none-any.whl` returns 200.
- Cache-Control headers match the design.

---

- [ ] **Task 5: Update `generate_html()` to reference two wheels**

**Estimated time: ~0.5 hours**

### Steps

1. In `webcompy/cli/_html.py`, update `generate_html()`:
   - Receive `bundled, pyodide_builtin` from `_discover_dependency_package_dirs()`.
   - Build `py_packages` list with two wheel URLs first, then C-extension deps.
2. In `generate_static_site()`, copy both wheels to `dist/_webcompy-app-package/` without version suffix.
3. Write a unit test.

### Acceptance Criteria

- Generated HTML contains both wheel URLs.
- Pure-Python dependencies are NOT listed in `py-config.packages`.
- C-extension dependencies (e.g., `numpy`) ARE listed.

---

- [ ] **Task 6: Add `version` to `AppConfig` and update version handling**

**Estimated time: ~0.5 hours**

### Steps

1. Add `version: str | None = None` to `AppConfig`.
2. Update `generate_app_version()` to accept an optional `version` override.
3. Use the version string for wheel METADATA but NOT for wheel URL.

### Acceptance Criteria

- `AppConfig(version="1.0.0")` results in wheel METADATA version `1.0.0`.
- Wheel URL remains stable without version suffix.
- When `version` is None, timestamp-based fallback is used.

---

- [ ] **Task 7: Update unit and e2e tests**

**Estimated time: ~1 hour**

### Steps

1. Update existing wheel builder tests to confirm `webcompy/cli/` is excluded.
2. Update existing HTML generation tests to expect two wheel URLs.
3. Run full test suite (`pytest tests/`) and fix any failures.

### Acceptance Criteria

- All existing tests pass.
- New tests for wheel split, cache headers, and HTML generation pass.
- `docs_src` app builds and serves correctly in dev mode.

---

## Dependencies

- None. This change is independent of hydration work.

## Specs to Update

- `openspec/specs/wheel-builder/spec.md` — add `make_browser_webcompy_wheel()` requirement.
- `openspec/specs/cli/spec.md` — update single-wheel requirement to two-wheel requirement, mention cache headers.
- `openspec/specs/app-config/spec.md` — add `AppConfig.version`.