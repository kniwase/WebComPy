# Proposal: Split Mode — Detached Wheel Serving for Browser Cache Optimization

## Summary

Add an optional split mode that serves the webcompy framework, application code, and pure-Python dependencies as separate wheels instead of a single bundled wheel. This enables browser cache optimization — when only the app code changes, the framework and dependency wheels can be served from cache.

## Motivation

1. **Cache efficiency**: In the default bundled mode, any code change (even a one-line app update) requires re-downloading the entire wheel containing webcompy + deps + app. Split mode allows independent caching of framework and dependency wheels.

2. **Bandwidth savings**: For apps with frequent updates but stable dependencies, split mode significantly reduces download size on each update.

3. **Incremental loading**: Future PyScript/Pyodide improvements may support parallel wheel loading, making split mode faster than bundled mode for initial load.

## Known Issues Addressed

- **PyScript multi-wheel timeout disproved**: The previously reported PyScript initialization timeout with multiple local wheel URLs in `packages` was tested against PyScript 2026.3.1 and did not reproduce (see Experiment Results below). Strategy A is confirmed viable.

## Non-goals

- This does not replace the default bundled mode — split mode is opt-in.
- This does not implement per-route code splitting.

## Dependencies

- **Requires** `feat-dependency-bundling` — the lock file, dependency classification, and wheel builder are prerequisites.

## Experiment Results (2026-05-05)

A spike was conducted against PyScript 2026.3.1 to evaluate loading strategies:

| Strategy | Description | Result |
|----------|------------|--------|
| **Strategy A** | Multiple local wheel URLs in `py-config.packages` | ✅ **Works** — no timeout, ~0.002s init overhead |
| **Strategy A (stress)** | 10 wheel URLs (with duplicates) in `py-config.packages` | ✅ **Works** — no timeout |
| Strategy B (serial) | `files` + `micropip.install()` with VFS path | ❌ Fails — micropip cannot parse bare filename as wheel |
| Strategy B (parallel) | `files` + `asyncio.gather(micropip.install(...))` | ❌ Fails — Pyodide `set_wheel_metadata` internal error |
| Strategy C | `files` + `emfs://` URL in `packages` | ❌ Fails — micropip cannot parse `emfs://` scheme |

**Conclusion**: Strategy A is the only viable loading strategy. The previously reported PyScript timeout with multiple local wheel URLs did not reproduce. Strategy B approaches all fail at the micropip/Pyodide integration level.

## Design

### Architecture

```
BUNDLED MODE (default, feat-dependency-bundling):
  ╔═════════════════════════════════════╗
  ║  myapp-{hash}-py3-none-any.whl     ║
  ║  ├── webcompy/ (excl. cli)         ║
  ║  ├── myapp/                        ║
  ║  ├── flask/                        ║
  ║  └── httpx/                        ║
  ╚═════════════════════════════════════╝
  packages = ["/_webcompy-app-package/myapp-{hash}-py3-none-any.whl", "numpy"]

SPLIT MODE (feat-split-mode, opt-in):
  ╔══════════════════════╗  ╔═════════════════════════════════════╗
  ║ webcompy             ║  ║  myapp-{hash}-py3-none-any.whl     ║
  ║  (excl. cli)         ║  ║  ├── myapp/                        ║
  ║  -{hash}-py3-any.whl ║  ║  ├── flask/                        ║
  ╚══════════════════════╝  ║  └── httpx/                        ║
                            ╚═════════════════════════════════════╝

  Strategy: two wheels (framework + app-with-deps) in packages
    packages = ["/_.../webcompy-0+sha.{hash8}-py3-none-any.whl",
                "/_.../myapp-0+sha.{hash8}-py3-none-any.whl",
                "numpy"]  # WASM from CDN only
```

### Configuration

```python
@dataclass
class AppConfig:
    ...
    wheel_mode: Literal["bundled", "split"] = "bundled"
```

### Cache Headers

| Wheel | Dev Server | Production (SSG) |
|-------|-----------|-------------------|
| Framework | `max-age=86400, must-revalidate` | ETag by hosting |
| Dependencies | `max-age=86400, must-revalidate` | ETag by hosting |
| App (dev) | `no-cache` | N/A |
| App (SSG) | N/A | ETag by hosting |

### Content-Hash Strategy

Both wheels use content-derived hash filenames:

| Wheel | Filename Pattern |
|-------|-----------------|
| App (with deps) | `{app_name}-0+sha.{hash8}-py3-none-any.whl` |
| Framework | `webcompy-0+sha.{hash8}-py3-none-any.whl` |

## Specs Affected

- `app-config` — add `wheel_mode` field
- `cli` — add `--wheel-mode` CLI flag, multi-wheel serving, cache headers per wheel type
- `wheel-builder` — reintroduce `make_browser_webcompy_wheel()`, per-dependency wheel generation with stable filenames
- `lockfile` — no changes needed (classification already tracks `is_wasm`)
- `dependency-resolver` — no changes needed

## Tasks

See `tasks.md` for full task breakdown.

- [x] **Task 0: Experiment** — determine viable loading strategy
- [x] **Task 1: Add `wheel_mode` to AppConfig**
- [x] **Task 2: Add `--wheel-mode` CLI flag**
- [x] **Task 3: Reintroduce `make_browser_webcompy_wheel()`**
- [x] **Task 4: Update `make_webcompy_app_package()` for split mode**
- [ ] **Task 5: Update HTML generation for split mode**
- [ ] **Task 6: Update dev server and SSG for two-wheel serving**
- [ ] **Task 7: Update E2E tests for split mode**
- [ ] **Task 8: Lint, typecheck, and test validation**
