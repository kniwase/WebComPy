## Why

`_is_wasm_in_pyodide_lock()` relies on the `package_type` field from the Pyodide lock to distinguish WASM packages from pure-Python ones. In Pyodide v0.29+, `package_type` is `"package"` for all packages, making the check always return `False`. The filename-based fallback (`"wasm32" in file_name`) is never reached because `package_type` is never `None`. This causes WASM packages (numpy, matplotlib, kiwisolver, contourpy, pillow) to be misclassified as pure-Python, downloaded as pure-Python wheels, and bundled into the app wheel — where they fail at runtime with `ModuleNotFoundError: No module named 'numpy._core._multiarray_umath'` because their C extensions are missing.

Additionally, `ClassifiedDependency` uses three overlapping boolean fields (`is_wasm`, `is_pure_python`, `in_pyodide_cdn`) to represent a mutually exclusive categorization, making the data model error-prone and hard to reason about.

## What Changes

- **BREAKING**: Replace `_is_wasm_in_pyodide_lock()` with a classification function that uses the wheel filename's platform tag as the single source of truth (PEP 425: `wasm32` = WASM, `any` = pure-Python). Remove all `package_type` checks.
- **BREAKING**: Replace `ClassifiedDependency.is_wasm`, `is_pure_python`, and `in_pyodide_cdn` with a `kind: PackageKind` enum (`WASM`, `CDN_PURE_PYTHON`, `LOCAL_PURE_PYTHON`). The `in_pyodide_cdn` information is derived from `kind != LOCAL_PURE_PYTHON`.
- Update `classify_dependencies()` and all consumers to use `PackageKind`.
- Update `generate_lockfile()` to populate `wasm_packages` / `pure_python_packages` based on `PackageKind`.
- Update `_server.py` and `_generate.py` to use `kind` for branching instead of `is_wasm` / `is_pure_python`.
- Add/update unit tests for the new classification logic.

## Capabilities

### New Capabilities
- `package-kind`: Defines the `PackageKind` enum and the canonical classification function that determines package kind from the Pyodide lock wheel filename.

### Modified Capabilities
- `dependency-resolver`: Replace overlapping booleans with `PackageKind`-based classification; remove `package_type` dependency from WASM detection.
- `lockfile`: Update `generate_lockfile()` to use `PackageKind` for populating `wasm_packages` and `pure_python_packages`.

## Impact

- `webcompy/cli/_dependency_resolver.py` — primary change: `ClassifiedDependency` dataclass, `classify_dependencies()`, WASM detection
- `webcompy/cli/_lockfile.py` — `generate_lockfile()` reads `kind` instead of `is_wasm`
- `webcompy/cli/_server.py` — branching logic uses `kind`
- `webcompy/cli/_generate.py` — branching logic uses `kind`
- `webcompy/cli/_pyodide_downloader.py` — no change (download pipeline unchanged)
- `webcompy/cli/_wheel_builder.py` — no change
- `tests/` — new/updated tests for classification