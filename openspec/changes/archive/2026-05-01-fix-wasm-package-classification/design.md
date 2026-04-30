## Context

The dependency resolver classifies packages as WASM or pure-Python to determine how they should be delivered to the browser. The current implementation uses `_is_wasm_in_pyodide_lock()` which checks `package_type` from the Pyodide lock file first, falling back to a filename heuristic (`"wasm32" in file_name`). In Pyodide v0.29+, `package_type` is `"package"` for all entries, so the fallback is never reached. This causes WASM packages to be misclassified as pure-Python, bundled into the app wheel without their C extensions, and fail at runtime.

The `ClassifiedDependency` dataclass uses three overlapping boolean fields (`is_wasm`, `is_pure_python`, `in_pyodide_cdn`) to represent a tripartite categorization, which is logically equivalent to an enum.

## Goals / Non-Goals

**Goals:**
- Fix WASM package detection so numpy, matplotlib, and other WASM packages load correctly in the browser
- Make classification logic robust against future Pyodide lock schema changes
- Replace overlapping booleans with a single `PackageKind` enum to eliminate invalid states
- Maintain the existing lockfile v2 schema (no schema change needed — `wasm_packages` and `pure_python_packages` already reflect the correct categorization)

**Non-Goals:**
- Supporting Pyodide versions before v0.27 (no backward compatibility needed)
- Changing the lockfile schema version (v2 is correct; the bug is in how we populate it)
- Changing the `serve_all_deps` behavior or the download/bundle pipeline
- Fixing the `_collect_package_files` filter (`.py`/`.pyi`/`py.typed` only) — that is a separate concern

## Decisions

### Decision 1: Use wheel filename platform tag as the single source of truth for WASM detection

**Choice**: Check `"wasm32" in file_name` only. Remove `package_type` check entirely.

**Rationale**: PEP 425 defines the wheel filename platform tag. Pure-Python wheels use `any`; WASM-compiled wheels use tags containing `wasm32`. This is the stable, spec-driven signal. `package_type` is an internal Pyodide metadata field that has changed meaning between versions (e.g., `"shared_library"` in v0.26, `"package"` in v0.29) and cannot be relied upon.

**Alternatives considered**:
- **Check `package_type` first, fall back to filename**: Keeps the bug — if `package_type` exists (which it always does now), the fallback is unreachable.
- **Check `package_type` in known WASM values, then fall back to filename**: Adds complexity for no benefit; `package_type` is not a reliable signal.
- **Check both `package_type` and filename with OR logic**: Over-engineered; filename alone is sufficient and unambiguous.

### Decision 2: Replace overlapping booleans with `PackageKind` enum

**Choice**: Introduce `PackageKind` enum with three values:
```
WASM              — Must be loaded from Pyodide CDN by name
CDN_PURE_PYTHON   — Available on CDN; can bundle or load by name
LOCAL_PURE_PYTHON  — Not on CDN; must bundle from local install
```

Replace `is_wasm: bool`, `is_pure_python: bool`, `in_pyodide_cdn: bool` on `ClassifiedDependency` with `kind: PackageKind`. Derive `in_pyodide_cdn` as `kind != LOCAL_PURE_PYTHON`.

**Rationale**: Three booleans can represent 8 states, but only 3 are valid (`WASM`, `CDN_PURE_PYTHON`, `LOCAL_PURE_PYTHON`). The enum makes invalid states unrepresentable and simplifies downstream branching.

**Alternatives considered**:
- **Keep booleans but fix the bug only**: Leaves the data model error-prone; easy to introduce invalid states in the future.
- **Use string literals instead of enum**: Works but loses type-safety and discoverability.

### Decision 3: Classification flow uses `PackageKind` throughout

**Choice**: `ClassifiedDependency.kind` drives the classification-to-lockfile mapping in `generate_lockfile()`. Downstream consumers that operate on `Lockfile` data (i.e., `PurePythonPackageEntry` and `WasmPackageEntry`) continue to use `in_pyodide_cdn` and other existing fields — these are part of the lockfile v2 schema and remain unchanged.

Mapping in `generate_lockfile()`:
```
PackageKind.WASM             → WasmPackageEntry  (in wasm_packages)
PackageKind.CDN_PURE_PYTHON  → PurePythonPackageEntry (in_pyodide_cdn=True)  (in pure_python_packages)
PackageKind.LOCAL_PURE_PYTHON → PurePythonPackageEntry (in_pyodide_cdn=False) (in pure_python_packages)
```

Note: `PurePythonPackageEntry.in_pyodide_cdn` is derived from `kind != LOCAL_PURE_PYTHON` during the `ClassifiedDependency → PurePythonPackageEntry` conversion, but the field itself remains on `PurePythonPackageEntry` as part of the lockfile schema. Functions like `validate_local_environment()`, `get_bundled_deps()`, and `get_cdn_pure_python_package_names()` operate on `Lockfile`/`PurePythonPackageEntry` objects, not on `ClassifiedDependency`, so they continue to use `in_pyodide_cdn` directly and require no changes.

Similarly, `_server.py` and `_generate.py` operate on `Lockfile` entries (`PurePythonPackageEntry`) for the download/bundle pipeline, using `entry.in_pyodide_cdn`. These paths are unchanged. The only consumer that switches from `is_wasm`/`is_pure_python`/`in_pyodide_cdn` to `kind` is `generate_lockfile()`.

**Rationale**: The lockfile schema already separates `wasm_packages` and `pure_python_packages`; the mapping is natural and requires no schema change. Limiting the `kind`-based branching to `generate_lockfile()` minimizes the scope of change while still fixing the root cause.

### Decision 4: Keep `_is_pure_python_package()` for local-only packages

**Choice**: Retain the existing `_is_pure_python_package(pkg_dir)` check (scanning for `.so`/`.pyd`/`.dylib` files) for packages not found in the Pyodide lock. This validates that local-only packages are actually pure-Python before bundling.

**Rationale**: For packages not in the Pyodide CDN, we still need to verify they don't have C extensions that can't run in the browser. The filename heuristic doesn't apply here since there's no CDN wheel to inspect.

## Risks / Trade-offs

- **[Pyodide changes wheel naming convention]** → Unlikely; PEP 425 is a standard. Even if they did, the check would fail safe (treat as pure-Python, which would produce a clearer error than the current silent misclassification).
- **[Breaking change for consumers of ClassifiedDependency]** → The change is internal to the CLI module; `ClassifiedDependency` is not part of the public API. Downstream code in `_lockfile.py`, `_server.py`, `_generate.py` will be updated in this change.
- **[Existing v1 lockfiles]** → Already handled; `load_lockfile()` returns `None` for v1, triggering regeneration. v2 lockfiles populated by the buggy code would be regenerated correctly on next build.