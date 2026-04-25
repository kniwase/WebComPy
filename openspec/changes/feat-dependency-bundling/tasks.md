# Tasks: Dependency Bundling — Dependency Resolution, Lock File, Stable URLs, and Browser Cache Strategy

- [ ] **Task 1: Implement dependency classification logic**

**Estimated time: ~1.5 hours**

### Steps

1. Create `webcompy/cli/_dependency_resolver.py`.
2. Implement `_is_pure_python_package(pkg_dir: pathlib.Path) -> bool`:
   - Walk `pkg_dir` recursively, check for `.so`, `.pyd`, `.dylib` files.
   - Return `True` if none found.
3. Implement `_find_package_dir(package_name: str) -> pathlib.Path | None`:
   - Use `importlib.util.find_spec()` to locate the package.
   - Return `spec.origin.parent` if found.
   - Handle single-file modules.
4. Implement `_resolve_transitive_deps(package_name: str) -> list[str]`:
   - Use `importlib.metadata` to walk `Requires-Dist`.
   - Skip extras-only dependencies.
   - Return all runtime dependency names (recursive).
5. Implement `classify_dependencies(dependencies: list[str], pyodide_lock: dict) -> tuple[list[ClassifiedDependency], list[str]]`:
   - For each direct dependency:
     - If in `pyodide_lock["packages"]` and `is_wasm`: classify as `pyodide_cdn`.
     - If in `pyodide_lock["packages"]` and not `is_wasm` (pure Python): classify as `bundled` (will be bundled locally).
     - If not in lock: find local package dir, check `.so`/`.pyd`.
       - Pure Python: classify as `bundled` with `source="explicit"`.
       - C extension: add to errors list.
   - **For ALL classified packages (including `pyodide_cdn` pure-Python), resolve transitive deps:**
     - If the package is in the Pyodide lock, use the `depends` field from the lock to discover transitive deps within the CDN.
     - Walk `depends` recursively, following each dep back into the Pyodide lock.
     - For transitive deps not in the Pyodide lock, fall back to `importlib.metadata` resolution.
   - Classify each transitive dep:
     - In Pyodide lock, WASM: classify as `pyodide_cdn`, `is_wasm=True`, `source="transitive"`.
     - In Pyodide lock, pure Python: classify as `pyodide_cdn`, `is_wasm=False`, `source="transitive"` → will be bundled.
     - Not in lock, pure Python locally: classify as `bundled` with `source="transitive"`.
     - Not in lock, C extension: add to errors.
6. Write comprehensive unit tests.

### Acceptance Criteria

- `classify_dependencies(["numpy"], lock)` classifies `numpy` as `pyodide_cdn` (WASM).
- `classify_dependencies(["httpx"], lock)` classifies `httpx` as `pyodide_cdn` with `is_wasm=False` (pure Python, bundled locally).
- `classify_dependencies(["httpx"], lock)` resolves `httpx`'s transitive dependencies via Pyodide lock `depends` field and local `importlib.metadata`.
- `classify_dependencies(["flask"], lock)` classifies `flask` as `bundled` (if not in lock) and resolves transitive deps.
- Transitive dependency not installed locally and not in Pyodide lock produces an error with instructions to install or add to dependencies.
- C extension not in lock produces an error message.
- `_is_pure_python_package()` returns `False` for `numpy`, `True` for `httpx`.
- When Pyodide lock is unavailable, C-extension packages produce warnings rather than errors.
- Pyodide lock `depends` field is used as a hint for discovering transitive dependencies within the CDN.

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

- [ ] **Task 3: Implement `webcompy-lock.json` read/write logic**

**Estimated time: ~1.5 hours**

### Steps

1. Create `webcompy/cli/_lockfile.py`.
2. Define `Lockfile` dataclass with `pyodide_version`, `pyscript_version`, `pyodide_packages`, `bundled_packages`.
3. Define `PyodidePackageEntry` dataclass with `version`, `file_name`, `is_wasm`.
4. Define `BundledPackageEntry` dataclass with `version`, `source`, `is_pure_python`.
5. Implement `load_lockfile()`, `save_lockfile()`, `generate_lockfile()`, `validate_lockfile()`.
6. Implement `get_bundled_deps(lockfile)` — always bundles pure-Python Pyodide packages (no `use_cdn` parameter).
7. Implement `get_pyodide_package_names(lockfile)` — returns only WASM package names (no `use_cdn` parameter).
8. Lock file position at `app_package_path / "webcompy-lock.json"`.
9. Write unit tests.

### Acceptance Criteria

- `generate_lockfile(["flask", "numpy"], "2026.3.1")` produces a `Lockfile` with `numpy` in `pyodide_packages` (WASM) and `flask` in `bundled_packages`.
- Pure-Python Pyodide packages (e.g., `httpx`) are placed in `bundled_packages`, not `pyodide_packages`.
- `get_bundled_deps()` returns pure-Python Pyodide packages for bundling.
- `get_pyodide_package_names()` returns only WASM package names.
- `save_lockfile()` + `load_lockfile()` roundtrips correctly.
- `validate_lockfile()` detects missing dependencies correctly.

---

- [ ] **Task 4: Add `webcompy lock` CLI command**

**Estimated time: ~0.5 hours**

### Steps

1. Modify `webcompy/cli/_argparser.py` to add a `lock` subcommand.
2. Create `webcompy/cli/_lock.py` with `lock_command()` function.
3. `lock_command()` discovers the app, calls `generate_lockfile()`, and saves the result.
4. Report C-extension errors to stderr and exit with code 1.
5. Print generated lock file path on success.

### Acceptance Criteria

- `webcompy lock` creates `webcompy-lock.json` in the app package directory.
- C-extension errors are printed to stderr.
- Exit code 0 on success, 1 on error.

---

- [ ] **Task 5: Integrate lock file into start/generate commands**

**Estimated time: ~0.5 hours**

### Steps

1. In `create_asgi_app()` and `generate_static_site()`:
   - Locate `webcompy-lock.json` at `app.config.app_package_path / "webcompy-lock.json"`.
   - Call `resolve_lockfile()`.
   - Use `get_bundled_deps(lockfile)` for wheel bundling.
   - Use `get_pyodide_package_names(lockfile)` for HTML generation (WASM only).
2. Handle network failures gracefully.

### Acceptance Criteria

- `webcompy start --dev` auto-generates lock file if missing.
- `webcompy generate` auto-generates lock file if missing.
- Stale lock files are regenerated.
- Network failures fall back gracefully.

---

- [ ] **Task 6: Update `make_webcompy_app_package()` for cli exclusion and bundled deps**

**Estimated time: ~1 hour**

### Steps

1. Add `_BROWSER_ONLY_EXCLUDE = {"cli"}` constant to `_wheel_builder.py`.
2. Modify `make_webcompy_app_package()` to exclude `webcompy/cli/` when bundling webcompy:
   - Filter the webcompy package files to exclude paths containing `cli` in their relative parts.
   - Filter the discovered packages to exclude `webcompy.cli` from `top_level.txt`.
3. Add `bundled_deps: list[tuple[str, pathlib.Path]] | None = None` parameter.
4. When `bundled_deps` is provided, extend `package_dirs` with the bundled dependency directories.
5. The wheel filename SHALL use the stable format `{app_name}-py3-none-any.whl`.
6. Remove `make_browser_webcompy_wheel()` (no longer needed — webcompy is bundled inside the app wheel).
7. Write unit tests.

### Acceptance Criteria

- `make_webcompy_app_package()` produces a wheel containing `webcompy/app/`, `webcompy/elements/`, etc.
- The wheel does NOT contain `webcompy/cli/` or any files under `webcompy/cli/`.
- `top_level.txt` lists `webcompy` and the app name (no `webcompy.cli`).
- `make_webcompy_app_package(..., bundled_deps=[("click", path)])` produces a wheel containing the `click/` directory.
- `top_level.txt` lists `webcompy`, the app name, and `click`.
- Wheel filename follows the stable naming convention.
- `make_browser_webcompy_wheel()` is removed.

---

- [ ] **Task 7: Update `generate_html()` for single-wheel and WASM-only packages**

**Estimated time: ~0.5 hours**

### Steps

1. Modify `generate_html()` to accept `pyodide_package_names: list[str] | None = None`.
2. Construct `py_packages` with single wheel URL, then WASM package names:
   ```python
   app_wheel_url = f"{base_url}_webcompy-app-package/{stable_filename}"
   py_packages = [app_wheel_url, *pyodide_package_names]
   ```
3. When `pyodide_package_names` is `None`, fall back to `app.config.dependencies`.
4. Remove `webcompy_wheel_url` (no separate framework wheel).
5. Update unit tests.

### Acceptance Criteria

- Generated HTML contains a single wheel URL.
- WASM packages appear as plain names in `py-config.packages`.
- Pure-Python bundled packages do NOT appear in `py-config.packages`.
- Backward compatibility when no lock file exists.

---

- [ ] **Task 8: Update server and SSG for single-wheel serving**

**Estimated time: ~0.5 hours**

### Steps

1. In `create_asgi_app()`:
   - Build single app wheel at startup (using `make_webcompy_app_package()` with `bundled_deps`).
   - Serve at stable URL: `/_webcompy-app-package/{app_name}-py3-none-any.whl`.
   - Set `Cache-Control: no-cache` in dev mode for the wheel.
   - Remove `make_browser_webcompy_wheel()` call.
   - Remove framework wheel Cache-Control header logic.
2. In `generate_static_site()`:
   - Build single app wheel (with cli exclusion and bundled deps).
   - Copy to `dist/_webcompy-app-package/`.
   - Pass `pyodide_package_names` (WASM only) to `generate_html()`.
3. Update unit tests.

### Acceptance Criteria

- `GET /_webcompy-app-package/{app_name}-py3-none-any.whl` returns 200.
- App wheel (dev) response includes `Cache-Control: no-cache`.
- SSG output contains single wheel file.
- No separate `webcompy-py3-none-any.whl` is generated.

---

- [ ] **Task 9: Add `AppConfig.version` and stable URL support**

**Estimated time: ~0.5 hours**

### Steps

1. Add `version: str | None = None` to `AppConfig` dataclass.
2. Update `generate_app_version()` to use `AppConfig.version` when provided, falling back to timestamp.
3. Ensure wheel METADATA contains the version, but wheel filename does NOT.
4. Remove `AppConfig.use_cdn` (no longer needed).
5. Write unit tests.

### Acceptance Criteria

- `AppConfig(version="1.0.0")` results in wheel METADATA `Version: 1.0.0`.
- Wheel URL remains stable without version suffix.
- `AppConfig()` (no version) falls back to timestamp-based METADATA version.
- `AppConfig.use_cdn` does not exist.

---

- [ ] **Task 10: Update unit and E2E tests**

**Estimated time: ~1.5 hours**

### Steps

1. Update existing wheel builder tests:
   - Verify `webcompy/cli/` is excluded from app wheel.
   - Verify `bundled_deps` packages appear in app wheel.
   - Verify stable filename convention.
   - Remove `make_browser_webcompy_wheel` tests.
2. Add new test files:
   - `tests/test_dependency_resolver.py` — classification, transitive resolution, `.so` detection.
   - `tests/test_lockfile.py` — lock file generation, save/load, validation.
   - `tests/test_pyodide_lock.py` — Pyodide lock fetching and caching (mocked HTTP).
3. Update HTML generation tests for single-wheel URL.
4. Update E2E tests to expect single wheel file, verify WASM-only packages in HTML.
5. Run full test suite (`pytest tests/ --tb=short`) and fix any failures.

### Acceptance Criteria

- All existing tests pass.
- New test files for dependency resolver, lock file, and Pyodide lock pass.
- `docs_src` app builds and serves correctly in dev mode.