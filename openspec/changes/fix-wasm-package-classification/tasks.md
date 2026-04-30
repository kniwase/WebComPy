## 1. Define PackageKind Enum and Update ClassifiedDependency

- [ ] 1.1 Add `PackageKind` enum to `_dependency_resolver.py` with values `WASM`, `CDN_PURE_PYTHON`, `LOCAL_PURE_PYTHON`
- [ ] 1.2 Replace `is_wasm`, `is_pure_python`, `in_pyodide_cdn` fields on `ClassifiedDependency` with `kind: PackageKind`
- [ ] 1.3 Add property or helper to derive `in_pyodide_cdn` from `kind != LOCAL_PURE_PYTHON` for backward-compatible read patterns

## 2. Fix WASM Detection Logic

- [ ] 2.1 Replace `_is_wasm_in_pyodide_lock()` with a classification function that uses `"wasm32" in file_name` only, removing all `package_type` checks
- [ ] 2.2 Update `classify_dependencies()` to use the new function and set `kind` on each `ClassifiedDependency`
- [ ] 2.3 Update `_resolve_all_transitives()` to use `PackageKind` for transitive dependency classification

## 3. Update Lockfile Generation

- [ ] 3.1 Update `generate_lockfile()` in `_lockfile.py` to populate `wasm_packages` / `pure_python_packages` based on `kind` instead of `is_wasm`. Note: `PurePythonPackageEntry.in_pyodide_cdn` remains in the lockfile schema — derive it from `kind != LOCAL_PURE_PYTHON` during the `ClassifiedDependency` → `PurePythonPackageEntry` conversion.
- [ ] 3.2 No change needed for `validate_local_environment()` — it operates on `Lockfile`/`PurePythonPackageEntry` which retains `in_pyodide_cdn` as a field, not on `ClassifiedDependency`.
- [ ] 3.3 No change needed for `get_bundled_deps()` — same as 3.2, it operates on `Lockfile`/`PurePythonPackageEntry`, not `ClassifiedDependency`.

## 4. Update Server and Generator Consumers

- [ ] 4.1 Update `_server.py` `create_asgi_app()` to use `kind` for branching (WASM → wasm_package_names, CDN_PURE_PYTHON → download/bundle or name list, LOCAL_PURE_PYTHON → bundled_deps)
- [ ] 4.2 Update `_generate.py` if it has similar branching logic using `is_wasm` / `is_pure_python`

## 5. Tests

- [ ] 5.1 Add unit tests for `PackageKind` enum and classification function with mock Pyodide lock data (v0.29 schema with `package_type: "package"` for all entries)
- [ ] 5.2 Add unit tests for `classify_dependencies()` verifying `kind` is set correctly for WASM, CDN pure-Python, and local pure-Python packages
- [ ] 5.3 Add unit test specifically for the regression case: numpy with `package_type: "package"` and `wasm32` in filename is classified as `PackageKind.WASM`
- [ ] 5.4 Update existing tests that reference `is_wasm`, `is_pure_python`, `in_pyodide_cdn` on `ClassifiedDependency`

## 6. Cleanup and Verification

- [ ] 6.1 Delete the `docs_src/webcompy-lock.json` file so it gets regenerated with correct v2 classifications on next build
- [ ] 6.2 Run `uv run ruff check .` and `uv run ruff format .` to ensure code style
- [ ] 6.3 Run `uv run pyright` to verify type-checking passes
- [ ] 6.4 Run `uv run python -m pytest tests/ --tb=short` to verify all tests pass