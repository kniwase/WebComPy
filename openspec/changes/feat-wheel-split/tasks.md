# Tasks: Wheel Split — Browser-Only Wheel, Dependency Resolution, Lock File, and Browser Cache Strategy

- [ ] **Task 1: Implement `make_browser_webcompy_wheel()`**

**Estimated time: ~1 hour**

### Steps

1. Open `webcompy/cli/_wheel_builder.py`.
2. Add `_BROWSER_ONLY_EXCLUDE = {"cli"}` constant.
3. Implement `make_browser_webcompy_wheel(webcompy_package_dir, dest, version)`:
   - Walk `webcompy/` directory recursively, excluding paths containing `cli` in their relative parts.
   - Include `.py`, `.pyi`, `py.typed`, `__init__.py`, `_version.py` files.
   - Call `_make_wheel()` or internal logic with `name="webcompy"`.
   - The wheel filename SHALL be `webcompy-py3-none-any.whl` (no version suffix).
   - The METADATA SHALL contain `Version: {version}`.
4. Add a stable-filename variant of `get_wheel_filename` or update it to support versionless filenames.
5. Write unit tests: `test_browser_wheel_excludes_cli`, `test_browser_wheel_contains_framework_packages`.

### Acceptance Criteria

- `make_browser_webcompy_wheel()` produces a valid `.whl` file.
- Extracting the wheel shows `webcompy/` with `app/`, `elements/`, `reactive/`, etc.
- No `webcompy/cli/` directory exists in the extracted wheel.
- `top_level.txt` lists `webcompy`.
- Wheel filename is `webcompy-py3-none-any.whl`.

---

- [ ] **Task 2: Implement Pyodide lock fetch and cache**

**Estimated time: ~1 hour**

### Steps

1. Create `webcompy/cli/_pyodide_lock.py`.
2. Implement `fetch_pyodide_lock(pyodide_version: str) -> dict`:
   - Check `~/.cache/webcompy/pyodide-lock-{version}.json`.
   - If cached, return parsed JSON.
   - Otherwise, fetch from `https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json`.
   - Save to cache directory, return parsed JSON.
   - On network failure with no cache, return `None` (caller handles fallback).
3. Implement `get_pyodide_version(pyscript_version: str) -> str`:
   - Map PyScript version to Pyodide version via `PYSCRIPT_TO_PYODIDE` dict.
   - Raise `ValueError` for unknown PyScript versions.
4. Write unit tests with mocked HTTP responses.

### Acceptance Criteria

- `fetch_pyodide_lock("0.29.3")` returns parsed `pyodide-lock.json`.
- Cache is used on second call.
- `get_pyodide_version("2026.3.1")` returns `"0.29.3"`.
- Network failure with cache returns cached data.
- Network failure without cache returns `None`.

---

- [ ] **Task 3: Implement dependency classification logic**

**Estimated time: ~1.5 hours**

### Steps

1. Create `webcompy/cli/_dependency_resolver.py`.
2. Implement `_is_pure_python_package(pkg_dir: pathlib.Path) -> bool`:
   - Walk `pkg_dir` recursively, check for `.so`, `.pyd`, `.dylib` files.
   - Return `True` if none found.
3. Implement `_find_package_dir(package_name: str) -> pathlib.Path | None`:
   - Use `importlib.util.find_spec()` to locate the package.
   - Return `spec.origin.parent` if found.
   - Handle single-file modules (e.g., `typing_extensions.py`).
4. Implement `_resolve_transitive_deps(package_name: str) -> list[str]`:
   - Use `importlib.metadata` to walk `Requires-Dist`.
   - Skip extras-only dependencies.
   - Return all runtime dependency names (recursive).
5. Implement `classify_dependencies(dependencies: list[str], pyodide_lock: dict) -> tuple[list[ClassifiedDependency], list[str]]`:
   - For each direct dependency:
     - If in `pyodide_lock["packages"]`: classify as `pyodide_cdn`.
     - If not: find local package dir, check `.so`/`.pyd`.
       - Pure Python: classify as `bundled` with `source="explicit"`.
       - C extension: add to errors list.
   - For each bundled package, resolve transitive deps and classify each.
   - Transitive deps in Pyodide lock: classify as `pyodide_cdn`.
   - Transitive deps pure Python not in lock: classify as `bundled` with `source="transitive"`.
   - Transitive deps C extension: add to errors.
6. Write comprehensive unit tests.

### Acceptance Criteria

- `classify_dependencies(["numpy"], lock)` classifies `numpy` as `pyodide_cdn`.
- `classify_dependencies(["httpx"], lock)` classifies `httpx` as `pyodide_cdn` and its transitive deps from lock as `pyodide_cdn`.
- `classify_dependencies(["flask"], lock)` classifies `flask` as `bundled` (if not in lock) and resolves transitive deps.
- C extension not in lock produces an error message.
- `_is_pure_python_package()` returns `False` for `numpy`, `True` for `httpx`.

---

- [ ] **Task 4: Update `make_webcompy_app_package()` for `bundled_deps`**

**Estimated time: ~0.5 hours**

### Steps

1. Modify `make_webcompy_app_package()` signature to accept `bundled_deps: list[tuple[str, pathlib.Path]] | None = None`.
2. When `bundled_deps` is provided, extend `package_dirs` with the bundled dependency directories.
3. Each bundled dep's top-level package name SHALL appear in `top_level.txt`.
4. The wheel filename SHALL use the stable format `{app_name}-py3-none-any.whl` (no version in URL, but version in METADATA).
5. Write unit tests.

### Acceptance Criteria

- `make_webcompy_app_package(..., bundled_deps=[("click", path)])` produces a wheel containing the `click/` directory.
- `top_level.txt` lists both the app name and `click`.
- Wheel filename follows the stable naming convention.

---

- [ ] **Task 5: Implement `webcompy-lock.json` read/write logic**

**Estimated time: ~1.5 hours**

### Steps

1. Create `webcompy/cli/_lockfile.py`.
2. Define `Lockfile` dataclass with `pyodide_version`, `pyscript_version`, `pyodide_packages`, `bundled_packages`.
3. Define `PyodidePackageEntry` dataclass with `version`, `file_name`.
4. Define `BundledPackageEntry` dataclass with `version`, `source`, `is_pure_python`.
5. Implement `load_lockfile(path: pathlib.Path) -> Lockfile | None`:
   - Parse JSON, validate `version` field is `1`.
   - Return `Lockfile` or `None` if file doesn't exist.
6. Implement `save_lockfile(lockfile: Lockfile, path: pathlib.Path)`:
   - Serialize to JSON with sorted keys and indentation.
7. Implement `generate_lockfile(dependencies, pyscript_version, pyodide_version=None)`:
   - Fetch Pyodide lock (or use cached).
   - Classify dependencies using `classify_dependencies()`.
   - Build `Lockfile` from classification results.
   - Return `(Lockfile, list[str])` where the list contains error messages.
8. Implement `validate_lockfile(lockfile: Lockfile, dependencies: list[str]) -> list[str]`:
   - Check that explicit entries in `bundled_packages` plus `pyodide_packages` keys cover all `dependencies`.
   - Return list of mismatches.
9. Write unit tests.

### Acceptance Criteria

- `generate_lockfile(["flask", "numpy"], "2026.3.1")` produces a `Lockfile` with `numpy` in `pyodide_packages` and `flask` in `bundled_packages`.
- `save_lockfile()` + `load_lockfile()` roundtrips correctly.
- `validate_lockfile()` detects missing dependencies correctly.
- C-extension errors are returned in the error list.

---

- [ ] **Task 6: Add `webcompy lock` CLI command**

**Estimated time: ~0.5 hours**

### Steps

1. Modify `webcompy/cli/_argparser.py` to add a `lock` subcommand.
2. Create `webcompy/cli/_lock.py` with `lock_command()` function.
3. `lock_command()` discovers the app, calls `generate_lockfile()`, and saves the result.
4. Report C-extension errors to stderr and exit with code 1.
5. Print generated lock file path on success.
6. Write unit tests.

### Acceptance Criteria

- `webcompy lock` creates `webcompy-lock.json` in the project root.
- C-extension errors are printed to stderr.
- Exit code 0 on success, 1 on error.

---

- [ ] **Task 7: Integrate lock file into start/generate commands**

**Estimated time: ~0.5 hours**

### Steps

1. In `create_asgi_app()` and `generate_static_site()`:
   - Locate `webcompy-lock.json` at `app.config.app_package_path.parent / "webcompy-lock.json"`.
   - Call `load_lockfile()`.
   - If not found or stale (`validate_lockfile()` returns mismatches), call `generate_lockfile()`.
   - Save the new lock file.
   - Use classification results to build `bundled_deps` for wheel generation.
   - Use `pyodide_packages` keys as `pyodide_package_names` for HTML generation.
2. Handle network failures gracefully (fall back to listing all dependencies in `py-config.packages`).

### Acceptance Criteria

- `webcompy start --dev` auto-generates lock file if missing.
- `webcompy generate` auto-generates lock file if missing.
- Stale lock files are regenerated.
- Network failures fall back gracefully.

---

- [ ] **Task 8: Update `generate_html()` for two-wheel packages config**

**Estimated time: ~1 hour**

### Steps

1. Modify `generate_html()` to accept `pyodide_package_names: list[str] | None = None`.
2. Construct `py_packages` with two wheel URLs first, then Pyodide CDN package names.
3. Stable URL format: `{base_url}_webcompy-app-package/webcompy-py3-none-any.whl` and `{base_url}_webcompy-app-package/{app_name}-py3-none-any.whl`.
4. When `pyodide_package_names` is `None`, fall back to `app.config.dependencies` (backward compatibility).
5. Update existing HTML generation tests.

### Acceptance Criteria

- Generated HTML contains both wheel URLs.
- Pyodide CDN packages appear as plain names (e.g., `"numpy"`) in `py-config.packages`.
- Bundled packages do NOT appear in `py-config.packages`.
- Backward compatibility when no lock file exists.

---

- [ ] **Task 9: Update server and SSG for two-wheel serving**

**Estimated time: ~1 hour**

### Steps

1. In `create_asgi_app()`:
   - Build both wheels at startup.
   - Serve at stable URLs: `/_webcompy-app-package/webcompy-py3-none-any.whl` and `/_webcompy-app-package/{app_name}-py3-none-any.whl`.
   - Set `Cache-Control` headers: framework `max-age=86400, must-revalidate`, app (dev) `no-cache`.
   - Set `Content-Type: application/zip`.
2. In `generate_static_site()`:
   - Build both wheels.
   - Copy to `dist/_webcompy-app-package/` with stable filenames.
   - Pass `pyodide_package_names` to `generate_html()`.
3. Write unit tests.

### Acceptance Criteria

- `GET /_webcompy-app-package/webcompy-py3-none-any.whl` returns 200.
- `GET /_webcompy-app-package/{app_name}-py3-none-any.whl` returns 200.
- Framework wheel response includes `Cache-Control: max-age=86400, must-revalidate`.
- App wheel (dev) response includes `Cache-Control: no-cache`.
- SSG output contains both wheel files with stable names.

---

- [ ] **Task 10: Add `AppConfig.version` and stable URL support**

**Estimated time: ~0.5 hours**

### Steps

1. Add `version: str | None = None` to `AppConfig` dataclass.
2. Update `generate_app_version()` or wheel-building code to use `AppConfig.version` when provided, falling back to timestamp.
3. Ensure wheel METADATA contains the version, but wheel filename does NOT.
4. Write unit tests.

### Acceptance Criteria

- `AppConfig(version="1.0.0")` results in wheel METADATA `Version: 1.0.0`.
- Wheel URL remains stable without version suffix.
- `AppConfig()` (no version) falls back to timestamp-based METADATA version.

---

- [ ] **Task 11: Update unit and E2E tests**

**Estimated time: ~1.5 hours**

### Steps

1. Update existing wheel builder tests:
   - Verify `webcompy/cli/` is excluded from browser wheel.
   - Verify `bundled_deps` packages appear in app wheel.
   - Verify stable filename convention.
2. Add new test files:
   - `tests/test_dependency_resolver.py` — classification, transitive resolution, `.so` detection.
   - `tests/test_lockfile.py` — lock file generation, save/load, validation.
   - `tests/test_pyodide_lock.py` — Pyodide lock fetching and caching (mocked HTTP).
3. Update existing HTML generation tests for two-wheel URLs.
4. Update existing server tests for cache headers and two-wheel serving.
5. Run full test suite (`pytest tests/ --tb=short`) and fix any failures.

### Acceptance Criteria

- All existing tests pass.
- New test files for dependency resolver, lock file, and Pyodide lock pass.
- `docs_src` app builds and serves correctly in dev mode.