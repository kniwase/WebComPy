# Proposal: Split Mode — Detached Wheel Serving for Browser Cache Optimization

## Summary

Add an optional split mode that serves the webcompy framework, application code, and pure-Python dependencies as separate wheels instead of a single bundled wheel. This enables browser cache optimization — when only the app code changes, the framework and dependency wheels can be served from cache. This mode requires resolving PyScript's current limitation with multiple local wheel URLs in `packages`.

## Motivation

1. **Cache efficiency**: In the default bundled mode, any code change (even a one-line app update) requires re-downloading the entire wheel containing webcompy + deps + app. Split mode allows independent caching of framework and dependency wheels.

2. **Bandwidth savings**: For apps with frequent updates but stable dependencies, split mode significantly reduces download size on each update.

3. **Incremental loading**: Future PyScript/Pyodide improvements may support parallel wheel loading, making split mode faster than bundled mode for initial load.

## Known Issues Addressed

None (new capability).

## Non-goals

- This does not replace the default bundled mode — split mode is opt-in.
- This does not implement per-route code splitting.

## Blocker

**PyScript issue**: Passing multiple local wheel URLs in `py-config.packages` causes initialization timeouts (confirmed in PyScript 2026.3.1). This change must first validate a workaround before committing to the split architecture.

## Dependencies

- **Requires** `feat-dependency-bundling` — the lock file, dependency classification, and wheel builder are prerequisites.

## Methodology: Experiment-First Approach

This change follows an **experiment-first** approach. Before committing to a specific implementation strategy, we will:

1. **Experiment with the `files` + `micropip` workaround first**
   - Use PyScript's `files` config to place wheel files in the virtual filesystem
   - Install them via `micropip.install()` in the startup script
   - Validate that this avoids the `packages` timeout issue

2. **Validate the approach end-to-end**
   - Confirm PyScript initialization completes reliably
   - Measure load time vs. bundled mode
   - Check for edge cases (WASM deps, transitive deps, large number of wheels)

3. **Based on experiment results, refine the design**
   - If `files` + `micropip` works: design splits around this mechanism
   - If not: investigate alternative strategies or wait for PyScript fix
   - Update specs and design documents based on findings

The specs, design, and tasks in this change are **preliminary** and will be revised based on experimental results. Do not treat them as final implementation requirements.

## Preliminary Design Direction

### Architecture

```
BUNDLED MODE (default, feat-dependency-bundling):
  ╔═════════════════════════════════════╗
  ║  myapp-py3-none-any.whl            ║
  ║  ├── webcompy/ (cli除外)           ║
  ║  ├── myapp/                        ║
  ║  ├── flask/                        ║
  ║  └── httpx/                        ║
  ╚═════════════════════════════════════╝
  packages = ["/_webcompy-app-package/myapp-py3-none-any.whl", "numpy"]

SPLIT MODE (feat-split-mode, opt-in):
  ╔══════════╗  ╔════════╗  ╔═══════╗  ╔═══════╗
  ║ webcompy ║  ║ myapp  ║  ║ flask ║  ║ httpx ║
  ║  .whl    ║  ║  .whl  ║  ║  .whl ║  ║  .whl ║
  ╚══════════╝  ╚════════╝  ╚═══════╝  ╚═══════╝
  
  Strategy A: packages (if PyScript fixes multi-wheel loading)
    packages = ["/_.../webcompy.whl", "/_.../myapp.whl",
                "/_.../flask.whl", "/_.../httpx.whl", "numpy"]

  Strategy B: files + micropip (experiment-first)
    files: place wheels in virtual filesystem
    startup: await micropip.install() for each wheel
    packages = ["numpy"]  (WASM from CDN only)
```

### Configuration

```python
@dataclass
class AppConfig:
    ...
    wheel_mode: Literal["bundled", "split"] = "bundled"
```

### Preliminary Experiment Plan

**Experiment 1: `files` + `micropip` approach**

```html
<script type="module" src="https://pyscript.net/releases/2026.3.1/core.js"></script>
<py-config>
  {
    "files": {
      "/wheels/webcompy-py3-none-any.whl": "/_webcompy-app-package/webcompy-py3-none-any.whl",
      "/wheels/myapp-py3-none-any.whl": "/_webcompy-app-package/myapp-py3-none-any.whl",
      "/wheels/flask-py3-none-any.whl": "/_webcompy-app-package/flask-py3-none-any.whl"
    },
    "packages": ["numpy"]
  }
</py-config>
<script type="py">
import asyncio
import micropip
async def main():
    await micropip.install("/wheels/webcompy-py3-none-any.whl")
    await micropip.install("/wheels/flask-py3-none-any.whl")
    from myapp.bootstrap import app
    app.run()
asyncio.ensure_future(main())
</script>
```

Measure:
- Initialization time (vs. bundled mode baseline)
- Reliability across reloads
- Error handling for missing/wrong wheels

**Experiment 2: Order-of-magnitude scaling**

Test with 5, 10, 20 pure-Py dependency wheels to measure:
- Whether initialization time scales linearly
- Whether there's a practical limit

### Cache Headers (Preliminary)

| Wheel | Dev Server | Production (SSG) |
|-------|-----------|-------------------|
| Framework | `max-age=86400, must-revalidate` | ETag by hosting |
| Dependencies | `max-age=86400, must-revalidate` | ETag by hosting |
| App (dev) | `no-cache` | N/A |
| App (SSG) | N/A | ETag by hosting |

## Specs Affected

- `app-config` — add `wheel_mode` field
- `cli` — add `--wheel-mode` CLI flag, multi-wheel serving
- `wheel-builder` — reintroduce `make_browser_webcompy_wheel()`, add per-dependency wheel generation
- `lockfile` — no changes needed (classification already tracks `is_wasm`)
- `dependency-resolver` — no changes needed

## Tasks

**Note: Tasks are preliminary and will be revised based on experiment results.**

- [ ] **Task 0: Experiment with `files` + `micropip` approach**
  - Build a minimal test with 2-3 local wheels using PyScript `files` config and `micropip.install()`
  - Measure initialization time vs. bundled mode
  - Document results and decide on implementation strategy
  - Update this proposal and design based on findings

- [ ] **Task 1: Add `wheel_mode` to AppConfig** (after experiment confirms approach)
- [ ] **Task 2: Implement split wheel generation** (after experiment confirms approach)
- [ ] **Task 3: Update HTML generation for split mode** (after experiment confirms approach)
- [ ] **Task 4: Update dev server and SSG for multi-wheel serving** (after experiment confirms approach)
- [ ] **Task 5: Add E2E tests for split mode** (after experiment confirms approach)