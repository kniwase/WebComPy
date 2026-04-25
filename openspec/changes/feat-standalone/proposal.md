# Proposal: Standalone — Orchestration Change for Complete Offline PWA Support

## Summary

Add a `standalone` configuration option that orchestrates `feat-deps-local-serving`, `feat-wasm-local-serving`, and `feat-pyscript-local-serving` to produce a fully self-contained application with zero external CDN requests. When enabled, all assets — PyScript runtime, Pyodide engine, WASM packages, and pure-Python packages — are downloaded at build time and served from the same origin.

## Motivation

While each local-serving change (`feat-deps-local-serving`, `feat-wasm-local-serving`, `feat-pyscript-local-serving`) can be enabled independently, developers typically want **complete offline capability** as a single configuration toggle. This change provides:

1. **Single config option**: `standalone=True` enables all three levels simultaneously.
2. **PWA readiness**: All same-origin assets are a prerequisite for ServiceWorker caching and PWA manifest generation (future changes).
3. **Air-gapped deployment**: A single `webcompy generate --standalone` produces a fully self-contained `dist/` directory.

## Known Issues Addressed

None (new capability).

## Non-goals

- This does not implement ServiceWorker registration or PWA manifest generation — those are future enhancements.
- This does not implement split/detached wheel mode — that is `feat-split-mode`.
- This does not change the default build mode (CDN mode remains default).

## Dependencies

- **Requires** `feat-dependency-bundling` — the lock file and single-bundle wheel are prerequisites.
- **Requires** at least one of: `feat-deps-local-serving`, `feat-wasm-local-serving`, or `feat-pyscript-local-serving` to be implemented first.
- **Full functionality requires all three**: `feat-deps-local-serving` + `feat-wasm-local-serving` + `feat-pyscript-local-serving`.

## Layered Architecture

```
Level 1: feat-dependency-bundling (prerequisite)
  WASM ─────── CDN
  純Py ─────── バンドル(ローカルインストール前提)
  PyScript ─── CDN

Level 3: feat-deps-local-serving
  純Py ─────── Pyodide CDNからDL → バンドル

Level 4: feat-wasm-local-serving
  WASM ─────── Pyodide CDNからDL → 同一オリジン配信

Level 5: feat-pyscript-local-serving
  PyScript ─── CDNからDL → 同一オリジン配信

Level 6: feat-standalone (this change)
  全てを同一オリジン配信 → 完全オフライン動作 ★
  standalone=True = deps_local=True + wasm_local=True + runtime_local=True
```

## Design

### Configuration

```python
@dataclass
class AppConfig:
    ...
    standalone: bool = False  # Enables all local serving modes
```

When `standalone=True`:
- Equivalent to `deps_serving="local-cdn"` + `wasm_serving="local"` + serving PyScript/Pyodide runtime locally.
- The CLI downloads all required assets at build time.
- Generated HTML references local asset URLs for everything.

### Orchestration Logic

```python
if config.standalone:
    deps_serving = "local-cdn"  # feat-deps-local-serving
    wasm_serving = "local"       # feat-wasm-local-serving
    runtime_local = True         # feat-pyscript-local-serving
```

### Build Pipeline (Standalone SSG)

```
webcompy generate --standalone
        │
        ▼
  Load/generate webcompy-lock.json
        │
        ▼
  Download PyScript assets (core.js, core.css)
  Download Pyodide runtime (pyodide.mjs, .wasm, .js, stdlib.zip)
  Download WASM packages from lock file
  Download pure-Python packages from Pyodide CDN (extract into bundle)
  Build single bundled wheel (webcompy + app + all pure-Py deps)
        │
        ▼
  dist/
  ├── _webcompy-assets/
  │   ├── core.js, core.css
  │   ├── pyodide.mjs, pyodide.asm.wasm, pyodide.asm.js
  │   ├── pyodide-lock.json
  │   ├── python_stdlib.zip
  │   └── packages/
  │       ├── numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl
  │       └── ...
  ├── _webcompy-app-package/
  │   └── myapp-py3-none-any.whl
  └── index.html (all local URLs, zero external requests)
```

### CLI

```bash
webcompy generate --standalone        # Full offline build
webcompy start --dev --standalone      # Dev server with offline assets
```

### PWA Extension (Future)

When `standalone=True`, future changes can add:
- `GenerateConfig.service_worker = True` → generate ServiceWorker script
- `GenerateConfig.manifest = {...}` → generate PWA manifest
- Offline caching strategies for same-origin assets

These are out of scope but `standalone=True` is the prerequisite.

## Important Notes

### Task Planning is Preliminary

This change depends on `feat-deps-local-serving`, `feat-wasm-local-serving`, and `feat-pyscript-local-serving`. The tasks below are **preliminary** and will be revised based on:

1. Implementation experience from prerequisite changes.
2. Edge cases discovered during dependency-local-serving experiments.
3. PyScript/Pyodide compatibility findings from runtime-local-serving.
4. Performance and size characteristics of standalone builds.

Task estimates and order may change significantly. Do not begin implementation until at least one prerequisite change is complete.

### Implementation May Reveal Need for Re-structuring

The boundary between this orchestration change and the individual local-serving changes may shift. For example:
- If `feat-pyscript-local-serving` already handles WASM package URLs, `feat-wasm-local-serving` may be simplified.
- If deps-local-serving and wasm-local-serving share download infrastructure, they may be merged.
- The `standalone` config option may subsume individual config options if per-level toggles prove unnecessary.

These decisions should be revisited during implementation.

## Specs Affected

- `app-config` — add `standalone: bool = False` flag
- `cli` — add `--standalone` CLI flag, orchestrate all local-serving modes
- `lockfile` — add `standalone_assets` section (coordinating all three local-serving changes)