# Tasks: Deps Local Serving — Same-Origin Pure-Python Package Serving

- [ ] **Task 1: Add `serve_all_deps` to AppConfig and redesign `ClassifiedDependency`**

**Estimated time: ~2 hours**

### Steps

1. Add `serve_all_deps: bool = True` to `AppConfig` dataclass.
2. Add `--serve-all-deps` / `--no-serve-all-deps` CLI flags to `start` and `generate` subcommands in `_argparser.py`.
3. Redesign `ClassifiedDependency` in `_dependency_resolver.py`:
   - Remove `source` values `"pyodide_cdn"` and `"fallback_cdn"`, keep only `"explicit"` and `"transitive"`.
   - Remove `is_bundled` and `is_cdn_package` properties.
   - Add fields: `in_pyodide_cdn: bool`, `pyodide_file_name: str | None`, `pyodide_sha256: str | None`.
4. Update `classify_dependencies()` to populate the new fields from Pyodide lock data:
   - For each package in Pyodide lock: set `in_pyodide_cdn=True`, populate `pyodide_file_name` and `pyodide_sha256` from the lock entry.
   - For packages not in the lock: set `in_pyodide_cdn=False`, leave CDN fields as `None`.
   - Set `source` to `"explicit"` for user-listed deps, `"transitive"` for auto-discovered.
5. Update `_resolve_all_transitives()` to set `source="transitive"` for discovered deps.
6. Update all callers that reference `is_bundled`, `is_cdn_package`, or `source="pyodide_cdn"`.
7. Write unit tests for `ClassifiedDependency` and `classify_dependencies()` with the new fields.

### Acceptance Criteria

- `AppConfig(serve_all_deps=True)` is the default.
- `classify_dependencies(["httpx"], lock)` produces a dep with `in_pyodide_cdn=True`, `pyodide_file_name="httpx-0.28.1-py3-none-any.whl"`, `source="explicit"`.
- `classify_dependencies(["flask"], lock)` produces a dep with `in_pyodide_cdn=False`, `source="explicit"` (when flask is not in lock).
- `classify_dependencies(["numpy"], lock)` produces a dep with `is_wasm=True`, `in_pyodide_cdn=True`, `source="explicit"`.
- `--serve-all-deps` and `--no-serve-all-deps` flags are accepted by `start` and `generate` commands.

---

- [ ] **Task 2: Implement Pyodide CDN wheel download with caching and verification**

**Estimated time: ~2 hours**

### Steps

1. Create `webcompy/cli/_pyodide_downloader.py`.
2. Implement `download_pyodide_wheel(file_name: str, pyodide_version: str, expected_sha256: str) -> pathlib.Path`:
   - Construct download URL: `https://cdn.jsdelivr.net/pyodide/v{pyodide_version}/full/{file_name}`.
   - Check cache at `~/.cache/webcompy/pyodide-packages/{pyodide_version}/{file_name}`.
   - If cached file exists and SHA256 matches `expected_sha256`, return cached path.
   - Otherwise, download using `urllib.request`.
   - Verify SHA256 of downloaded data against `expected_sha256`.
   - Raise `PyodideDownloadError` on verification failure, network failure, or invalid data.
   - Save to cache directory.
   - Return path to cached file.
3. Implement `extract_wheel(wheel_path: pathlib.Path, dest: pathlib.Path) -> list[tuple[str, pathlib.Path]]`:
   - Extract `.whl` (ZIP) to `dest`.
   - Read `top_level.txt` from the wheel's `.dist-info/` to discover package names.
   - Return list of `(package_name, package_dir)` tuples.
4. Write unit tests with mocked HTTP and temporary directories.

### Acceptance Criteria

- `download_pyodide_wheel("httpx-0.28.1-py3-none-any.whl", "0.29.3", expected_sha256)` downloads and caches the wheel.
- Second call returns cached path without network request.
- SHA256 mismatch raises `PyodideDownloadError`.
- Network failure raises `PyodideDownloadError`.
- `extract_wheel()` correctly returns package name and directory path.

---

- [ ] **Task 3: Redesign lock file schema to v2**

**Estimated time: ~2 hours**

### Steps

1. Update `LOCKFILE_VERSION` to `2` in `_lockfile.py`.
2. Replace `PyodidePackageEntry` with `WasmPackageEntry` (version, file_name, source).
3. Replace `BundledPackageEntry` with `PurePythonPackageEntry` (version, source, in_pyodide_cdn, pyodide_file_name, pyodide_sha256).
4. Update `Lockfile` dataclass:
   - `pyodide_packages` -> `wasm_packages: dict[str, WasmPackageEntry]`
   - `bundled_packages` -> `pure_python_packages: dict[str, PurePythonPackageEntry]`
5. Update `to_dict()` and `from_dict()` for v2 schema.
6. Update `load_lockfile()` to reject v1 lock files (return `None` to trigger regeneration).
7. Update `save_lockfile()` to write v2 format.
8. Update `generate_lockfile()` to populate new fields:
   - WASM deps -> `wasm_packages`.
   - Pure-Python deps -> `pure_python_packages` with `in_pyodide_cdn`, `pyodide_file_name`, `pyodide_sha256`.
9. Update `validate_lockfile()` for new field names.
10. Update `validate_local_environment()` to consider `in_pyodide_cdn` and `serve_all_deps`:
    - CDN-available + `serve_all_deps=True` → warning if missing locally (not error).
    - Local-only → error if missing locally (regardless of `serve_all_deps`).
11. Update `get_bundled_deps()`:
    - When `serve_all_deps=True`: return all pure-Python packages (CDN ones will be resolved via download in Task 4, local ones via `pkg_dir`).
    - When `serve_all_deps=False`: return only pure-Python packages with `in_pyodide_cdn=False`.
12. Add `get_cdn_pure_python_package_names(lockfile) -> list[str]`: return names of pure-Python packages with `in_pyodide_cdn=True` (for `serve_all_deps=False` HTML generation).
13. Rename `get_pyodide_package_names()` to `get_wasm_package_names()` for clarity (same behavior: WASM-only names).
14. Update `export_requirements()` and sync functions for new field names.
15. Write unit tests.

### Acceptance Criteria

- `generate_lockfile(["httpx", "flask", "numpy"], "2026.3.1")` produces a `Lockfile` with `numpy` in `wasm_packages`, `httpx` and `flask` in `pure_python_packages`.
- `httpx` entry has `in_pyodide_cdn=True`, `pyodide_file_name`, `pyodide_sha256`.
- `flask` entry has `in_pyodide_cdn=False`, no CDN fields.
- Loading a v1 lock file returns `None` (triggers regeneration).
- `save_lockfile()` + `load_lockfile()` roundtrips correctly.
- `get_bundled_deps(serve_all_deps=True)` returns only local-only pure-Python packages (CDN packages are handled via download pipeline).
- `get_bundled_deps(serve_all_deps=False)` returns only local-only pure-Python packages.
- `get_cdn_pure_python_package_names()` returns only CDN-available names.
- `validate_local_environment()` reports warning (not error) for missing CDN-available packages when `serve_all_deps=True`.

---

- [ ] **Task 4: Integrate download-extract-bundle pipeline**

**Estimated time: ~1.5 hours**

### Steps

1. In `create_asgi_app()` and `generate_static_site()`, after lock file resolution:
   - When `serve_all_deps=True`:
     - For each pure-Python package with `in_pyodide_cdn=True`:
       - Call `download_pyodide_wheel()` with file_name, pyodide_version, sha256.
       - Call `extract_wheel()` to a temporary directory.
       - Collect `(package_name, package_dir)` tuples.
     - For pure-Python packages with `in_pyodide_cdn=False`:
       - Use existing `get_bundled_deps()` logic (find local package dir).
     - Pass all collected tuples as `bundled_deps` to `make_webcompy_app_package()`.
   - When `serve_all_deps=False`:
     - Use `get_bundled_deps(serve_all_deps=False)` (only local-only packages).
2. Handle download errors gracefully: report error, fail build.
3. Write integration tests.

### Acceptance Criteria

- `serve_all_deps=True`: CDN packages are downloaded, extracted, and bundled.
- `serve_all_deps=False`: only local-only packages are bundled.
- Download failure causes build to fail with descriptive error.
- The app wheel contains CDN-downloaded packages when `serve_all_deps=True`.

---

- [ ] **Task 5: Update HTML generation and CLI flag integration**

**Estimated time: ~1 hour**

### Steps

1. Update `generate_html()` to accept `cdn_pure_python_names: list[str] | None = None` parameter.
2. When `cdn_pure_python_names` is provided (non-empty), append them to `py_packages` after WASM names.
3. In `create_asgi_app()` and `generate_static_site()`:
   - When `serve_all_deps=True`: pass `cdn_pure_python_names=[]` (empty — all bundled).
   - When `serve_all_deps=False`: pass `cdn_pure_python_names=get_cdn_pure_python_package_names(lockfile)`.
4. Wire `--serve-all-deps` / `--no-serve-all-deps` CLI flags to override `AppConfig.serve_all_deps`.
5. Write unit tests.

### Acceptance Criteria

- `serve_all_deps=True`: HTML `py-config.packages` contains only app wheel URL + WASM names. No pure-Python CDN names.
- `serve_all_deps=False`: HTML `py-config.packages` contains app wheel URL + WASM names + CDN pure-Python names.
- CLI flags correctly override `AppConfig.serve_all_deps`.

---

- [ ] **Task 6: Add local importlib.metadata transitive fallback**

**Estimated time: ~1.5 hours**

### Steps

1. Restore `_resolve_transitive_deps_local()` function from pre-`feat-dependency-bundling` code (was removed in commit `841d866`), but as a best-effort fallback:
   - Use `importlib.metadata.requires()` to walk `Requires-Dist` for packages not in Pyodide lock.
   - Skip extras-only dependencies, dev/test dependencies.
   - Return discovered dependency names.
2. In `_resolve_all_transitives()`, for packages with `in_pyodide_cdn=False` and `pkg_dir is not None`:
   - Walk Pyodide lock `depends` first (may find CDN-available transitives).
   - Then use `_resolve_transitive_deps_local()` as best-effort for remaining transitives.
   - Classify each discovered transitive:
     - If in Pyodide lock: classify normally with CDN metadata.
     - If not in lock but found locally: classify as `in_pyodide_cdn=False`, `is_pure_python=True`.
     - If not in lock and not found locally: report warning (not error), skip.
3. Write unit tests.

### Acceptance Criteria

- `flask` (not in Pyodide lock, locally installed) resolves `click`, `jinja2`, `itsdangerous` as transitive deps.
- `jinja2` (found in Pyodide lock via local walk) gets `in_pyodide_cdn=True` with CDN metadata.
- `click` (not in Pyodide lock, locally found) gets `in_pyodide_cdn=False`.
- Missing transitive dep produces warning, not error.

---

- [ ] **Task 7: Update existing unit and E2E tests**

**Estimated time: ~2 hours**

### Steps

1. Update `tests/test_dependency_resolver.py` for new `ClassifiedDependency` fields and `classify_dependencies()` behavior.
2. Update `tests/test_lockfile.py` for v2 schema, new entry types, and `load_lockfile()` v1 rejection.
3. Update `tests/test_lockfile_sync.py` for v2 schema field names (`wasm_packages`/`pure_python_packages`).
4. Update `tests/test_pyodide_lock.py` if needed.
5. Update `tests/test_wheel_builder.py` for `bundled_deps` with CDN-downloaded package directories.
6. Add new test file `tests/test_pyodide_downloader.py` for download, cache, and extraction logic.
7. Update E2E tests to verify:
   - `serve_all_deps=True`: app wheel contains CDN packages, HTML has no CDN pure-Python names.
   - `serve_all_deps=False`: HTML includes CDN pure-Python names in `py-config.packages`.
8. Add `e2e-matrix` entry in `.github/workflows/ci.yml` if new E2E test files are created.
9. Run full test suite and fix failures.

### Acceptance Criteria

- All existing tests pass.
- New test files for downloader pass.
- E2E tests verify both `serve_all_deps` modes.
- CI matrix updated for new E2E test files.