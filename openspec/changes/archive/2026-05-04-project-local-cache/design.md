## Context

WebComPy's standalone mode (`runtime_serving="local"` / `wasm_serving="local"`) downloads three categories of files from Pyodide/PyScript CDNs:

1. **PyScript core assets** (`core.js`, `core.css`)
2. **Pyodide runtime assets** (`pyodide.mjs`, `pyodide.asm.wasm`, `pyodide.asm.js`, `python_stdlib.zip`, `pyodide-lock.json`)
3. **WASM wheels** (`.whl` files for WASM-dependent packages like numpy)

Currently, categories 1 and 2 are cached in `~/.cache/webcompy/runtime-assets/{pyscript_version}/`, while category 3 is cached in `~/.cache/webcompy/pyodide-packages/{pyodide_version}/`. All downloaders hardcode these paths using `CACHE_DIR` module-level constants.

For dev server mode, the current implementation downloads into `TemporaryDirectory`, reads everything into memory with `read_bytes()`, and serves `Response(content=bytes)`. This is wasteful for large files (Pyodide WASM is ~8MB, `python_stdlib.zip` is ~5MB).

For SSG mode, the current implementation also uses `TemporaryDirectory` as a staging area before copying to `dist/`.

## Goals / Non-Goals

**Goals:**
- Move all download caching from `~/.cache/webcompy/` to `{app_package_path}/.webcompy_modules/`
- Eliminate `TemporaryDirectory` usage for runtime and WASM assets in both dev server and SSG
- Serve dev server assets directly from disk using `FileResponse`
- Auto-create `.gitignore` in `.webcompy_modules/` so it is never git-tracked
- Preserve SHA256 verification logic exactly as-is

**Non-Goals:**
- No automatic migration of `~/.cache/webcompy/` contents
- No cache eviction / size limits for `.webcompy_modules/`
- No customization of `.webcompy_modules/` location
- No change to how CDN pure-Python wheels are extracted for bundling (`serve_all_deps=True`) — temporary extraction still needed there

## Decisions

### Decision: Cache location is `{app_package_path}/.webcompy_modules/`

**Rationale:** The app package directory (`app.config.app_package_path`) is the most deterministic and correct location because:
- It is already where `webcompy-lock.json` lives, making the cache physically adjacent to its lock file
- It naturally isolates caches per-application when multiple apps exist in a monorepo
- It requires no "project root discovery" heuristic (unlike `pyproject.toml` search)
- It works correctly regardless of `--app` flag usage

**Alternative considered:** Project root (where `pyproject.toml` lives). Rejected because multiple WebComPy apps in one repo would share a cache, which defeats the isolation benefit.

### Decision: Use `FileResponse` for all disk-based serving in dev server

**Rationale:** `starlette.responses.FileResponse` streams from disk using `sendfile` on supported platforms, avoiding memory copies entirely. The current `Response(content=bytes)` approach loads the entire file into process memory before sending.

**Impact:**
- Runtime asset routes and WASM asset routes change from closure-based `Response` to `FileResponse`
- The `runtime_asset_files` dict changes from `dict[str, tuple[bytes, str]]` to `dict[str, pathlib.Path]` (or we remove the dict entirely and compute paths on-the-fly)

### Decision: Eliminate `TemporaryDirectory` for runtime and WASM assets, keep for CDN wheel extraction

**Rationale:**
- Runtime assets and WASM wheels are now cached in `.webcompy_modules/` permanently. SSG can copy directly from there to `dist/`.
- CDN pure-Python wheels still need to be extracted before bundling into the app wheel. This is a transient operation, so `TemporaryDirectory` remains appropriate.

### Decision: `.gitignore` content is `*` (ignore everything)

**Rationale:** Simple and effective. Users should never manually edit files in `.webcompy_modules/`. The directory is entirely machine-managed.

### Decision: Downloader functions accept `modules_dir` parameter instead of hardcoded `CACHE_DIR`

**Rationale:** Makes the cache location explicit and testable. All three downloader modules (`_pyodide_downloader.py`, `_runtime_downloader.py`, `_pyodide_lock.py`) gain a `modules_dir: pathlib.Path` parameter.

**Signature changes:**

```python
# _runtime_downloader.py
def download_runtime_assets(
    pyodide_version: str,
    pyscript_version: str,
    modules_dir: pathlib.Path,  # replaces CACHE_DIR usage
    dest_dir: pathlib.Path | None = None,  # if None, uses modules_dir directly
) -> dict[str, tuple[pathlib.Path, str]]:
    ...

# _pyodide_downloader.py
def download_pyodide_wheel(
    file_name: str,
    pyodide_version: str,
    expected_sha256: str,
    modules_dir: pathlib.Path,  # replaces CACHE_DIR usage
) -> pathlib.Path:
    ...

def download_wasm_wheels(
    lockfile: Lockfile,
    modules_dir: pathlib.Path,  # new parameter
) -> dict[str, pathlib.Path]:
    ...

# _pyodide_lock.py
def fetch_pyodide_lock(
    pyodide_version: str,
    modules_dir: pathlib.Path,  # replaces CACHE_DIR usage
) -> dict:
    ...
```

## Risks / Trade-offs

**[Risk] First build after this change re-downloads everything**
→ **Mitigation:** This is expected one-time behavior. The old `~/.cache/webcompy/` is simply abandoned. We accept this cost for the improved architecture.

**[Risk] Parallel server starts race on creating `.webcompy_modules/` and `.gitignore`**
→ **Mitigation:** `mkdir(parents=True, exist_ok=True)` is idempotent. `.gitignore` creation uses `if not exists(): write()` which is harmless if the race occurs (both write the same content).

**[Risk] `FileResponse` may not be available or behave differently across Starlette versions**
→ **Mitigation:** `FileResponse` is part of `starlette.responses`, which is already a project dependency. It has been stable since Starlette 0.1.

**[Risk] Tests mock `CACHE_DIR` module-level constant**
→ **Mitigation:** Tests need updating to pass `modules_dir` parameter instead. This is mechanical and covered in the task list.

## Migration Plan

No user migration needed. The change is transparent:
1. Old `~/.cache/webcompy/` is left untouched but ignored
2. First dev server / SSG run with local serving populates `.webcompy_modules/`
3. All subsequent runs use the new cache

## Open Questions

None at this time.
