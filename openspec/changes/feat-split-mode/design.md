# Design: Split Mode — Detached Wheel Serving for Browser Cache Optimization

## Design Decisions

### D1: Split mode is opt-in with confirmed loading strategy
The default mode remains bundled (single wheel). Split mode requires explicit `wheel_mode: "split"` in `AppConfig`.
A spike experiment (`.tmp/experiment/`) confirmed that **multiple local wheel URLs in `py-config.packages`** works reliably against PyScript 2026.3.1 with no timeout issues.

### D2: Multiple local wheel URLs in `packages` is the loading strategy
PyScript's `packages` config supports listing multiple local wheel URLs alongside WASM package names from the CDN.
Each local wheel URL points to a file served from `/_webcompy-app-package/`.

Example config for split mode with 3 dependencies:
```
packages = [
    "/_webcompy-app-package/webcompy-py3-none-any.whl",       # framework (no hash)
    "/_webcompy-app-package/flask-py3-none-any.whl",          # dependency (no hash)
    "/_webcompy-app-package/httpx-py3-none-any.whl",          # dependency (no hash)
    "/_webcompy-app-package/myapp-0+sha.{hash8}-py3-none-any.whl",  # app (content-hash)
    "numpy",  # WASM from CDN
]
```

### D3: `AppConfig.wheel_mode` controls bundling strategy
```python
@dataclass
class AppConfig:
    wheel_mode: Literal["bundled", "split"] = "bundled"
```
When `wheel_mode="split"`, the build produces separate wheels for webcompy, each dependency, and the app.

### D4: Cache headers differ per wheel type in split mode
In dev mode:
- Framework and dependency wheels: `Cache-Control: max-age=86400, must-revalidate`
- App wheel: `Cache-Control: no-cache` (changes frequently during development)

In SSG/production: ETag/Last-Modified by hosting provider.

### D5: Content-hash only for app wheel
- App wheel: retains the existing content-hash pattern (`myapp-0+sha.{hash8}-py3-none-any.whl`)
- Framework wheel: stable filename (`webcompy-py3-none-any.whl`)
- Dependency wheels: stable filenames (`{dep_name}-py3-none-any.whl`)

The content-hash on the app wheel ensures cache busting on application changes.
Framework and dependency wheels use stable filenames with long-lived cache headers.

### D6: Interaction with existing serving modes

| Combination | Behavior |
|------------|----------|
| `wheel_mode="split"` + `serve_all_deps=True` | All pure-Python deps get their own wheels; CDN pure-Python packages downloaded and made into wheels |
| `wheel_mode="split"` + `serve_all_deps=False` | Only non-CDN pure-Python deps get wheels; CDN packages loaded by name |
| `wheel_mode="split"` + `standalone=True` | All local-serving enabled; WASM packages served locally as individual wheels |
| `wheel_mode="split"` + `wasm_serving="local"` | WASM wheels served as individual files (same as current behavior, compatible) |

## Architecture

```
BUNDLED MODE (default):
  ╔═════════════════════════════════════╗
  ║  myapp-{hash}-py3-none-any.whl     ║
  ║  ├── webcompy/ (excl. cli)         ║
  ║  ├── myapp/                        ║
  ║  ├── flask/                        ║
  ║  └── httpx/                        ║
  ╚═════════════════════════════════════╝
  packages = ["/_webcompy-app-package/myapp-{hash}-py3-none-any.whl", "numpy"]

SPLIT MODE (this change, opt-in):
  ╔══════════╗  ╔════════╗  ╔═══════╗  ╔═══════╗
  ║ webcompy ║  ║ myapp  ║  ║ flask ║  ║ httpx ║
  ║  .whl    ║  ║  .whl  ║  ║  .whl ║  ║  .whl ║
  ╚══════════╝  ╚════════╝  ╚═══════╝  ╚═══════╝

  packages = [
      "/_.../webcompy-py3-none-any.whl",           # framework
      "/_.../flask-py3-none-any.whl",              # dep
      "/_.../httpx-py3-none-any.whl",              # dep
      "/_.../myapp-0+sha.{hash8}-py3-none-any.whl", # app (hash)
      "numpy",                                     # WASM CDN
  ]
```

## Specs Affected

- `app-config` — add `wheel_mode` field
- `cli` — add `--wheel-mode` CLI flag, multi-wheel serving, per-type cache headers
- `wheel-builder` — reintroduce `make_browser_webcompy_wheel()`, per-dependency wheel generation with stable filenames

## Non-goals

- This does not replace the default bundled mode.
- This does not implement per-route code splitting.
- This does not change WASM or pure-Python dependency handling.

## Reference Implementation

A prior implementation exists in commit `d474c65` on branch `feat/wheel-split`.
Key reusable patterns:
- `make_browser_webcompy_wheel()` — produces `webcompy-py3-none-any.whl` with `cli/` excluded
- `get_stable_wheel_filename()` — generates `{name}-py3-none-any.whl` without version/hash
- Cache header logic: check filename to determine `max-age=86400` vs `no-cache`
- E2E test updates: expect 2+ wheel files, check both URLs in HTML

These patterns need to be updated for:
- Content-hash integration (app wheel uses hash, others use stable names)
- Interaction with `serve_all_deps`, `wasm_serving`, `standalone` modes
- Dev server disk-based serving (current code uses `FileResponse` for assets)
