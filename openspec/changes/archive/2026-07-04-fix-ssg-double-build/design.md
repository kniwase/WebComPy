## Context

`_generate.py` currently calls `resolve_build_artifacts()` twice during SSG:

1. **Direct call** (line 69): to get wheel bytes for writing static files (`app_package_files`, `wasm_asset_files`, `runtime_asset_files`)
2. **Indirect via `create_asgi_app()`** (line 126): to build the HTML generator with wheel filenames

Because `generate_app_version()` uses `datetime.now()`, the two calls can produce different intermediate versions, which leads to different content-hash wheel filenames. The HTML references wheel filenames from call 2, but the actual files on disk are from call 1 — causing 404 errors in the browser and `zipfile.BadZipFile` from micropip.

The root cause is a design gap in the SSG-via-SSR refactoring: `create_asgi_app()` doesn't expose its `BuildArtifacts` to callers, forcing callers who need artifacts to call `resolve_build_artifacts()` themselves.

## Goals / Non-Goals

**Goals:**
- Eliminate the double `resolve_build_artifacts()` call in `_generate.py`
- Make `generate_app_version()` deterministic when no explicit version is configured
- Remove dead code (`app_version` parameter in `generate_html()`)
- Simplify `_generate.py` by removing duplicate resource management

**Non-Goals:**
- Refactor `_content_hash_wheel` or the wheel-building pipeline
- Add an implicit caching layer for build artifacts
- Change the public API of `_ServingApp` beyond adding `artifacts`

## Decisions

### Decision 1: Add `artifacts: BuildArtifacts` to `_ServingApp`

Add a typed field to the wrapper so callers can read build results without re-resolving.

**Alternative considered**: Optional `artifacts=` parameter on `create_asgi_app()`. Rejected because it inverts the relationship — the caller would build first, then pass to `create_asgi_app()`. This duplicates `resolve_build_artifacts()` call sites (`run_server()` would still call it internally). The `_ServingApp.artifacts` approach keeps `create_asgi_app()` as the single owner of build resolution.

### Decision 2: Remove standalone `resolve_build_artifacts()` call from `_generate.py`

`_generate.py` will call `create_asgi_app()` first, then use `serving.artifacts` for all file writing. The `cdn_temp_dir_obj` lifecycle is already managed by `create_asgi_app()` internally (CI review fix from `feat-ssg-via-ssr`), so the try/finally block in `_generate.py` becomes unnecessary.

### Decision 3: Replace `datetime.now()` with `"0.0.0"` in `generate_app_version()`

The intermediate version from `generate_app_version()` is used only to build the initial wheel. `_content_hash_wheel()` then replaces the version with `0+sha.{digest}` — the intermediate version never appears in the final wheel or any external interface.

**Alternative considered**: Source file hash. Rejected because it adds complexity (needs access to app package path, file I/O) for a value that is immediately discarded. The content hash already provides true content-based identification.

**Why `"0.0.0"` is safe**: The intermediate version appears only in the METADATA and dist-info directory name of the temporary wheel inside a `TemporaryDirectory`. After `_content_hash_wheel` repackages it, the temporary wheel is deleted, and the final wheel has `Version: 0+sha.{digest}` in its METADATA. `BuildArtifacts.app_version` is passed to `generate_html()` but never referenced in that function — it's dead data.

### Decision 4: Remove unused `app_version` from `generate_html()`

`_generate_html_impl()` receives `app_version` but never reads it. Remove it from both `generate_html()` and `_generate_html_impl()` signatures, and from the `partial()` binding in `create_asgi_app()`.

## Risks / Trade-offs

- **Risk**: Removing `app_version` from `generate_html()` affects callers outside `_server.py`. → **Mitigation**: The only call site is `create_asgi_app()` through `partial()`. No external consumer calls `generate_html()` directly.
- **Risk**: `"0.0.0"` as intermediate version could theoretically collide if something reads it. → **Mitigation**: Nothing reads the intermediate version. The final version is always the content hash.
