# Design: Split Mode — Detached Wheel Serving for Browser Cache Optimization

## Design Decisions

### D1: Split mode is opt-in and experiment-first
The default mode remains bundled (single wheel). Split mode requires explicit `wheel_mode: "split"` in `AppConfig`. This change follows an experiment-first approach — the `files` + `micropip` workaround for PyScript's multiple local wheel URL timeout must be validated before committing to the architecture.

### D2: `files` + `micropip` workaround is the primary loading strategy
PyScript's `packages` config with multiple local wheel URLs causes initialization timeouts (confirmed in PyScript 2026.3.1). The workaround uses PyScript's `files` config to place wheel files in the virtual filesystem, then installs them via `micropip.install()` in the startup script.

### D3: Experiments determine the final architecture
Before implementation, the following must be validated:
- Experiment 1: `files` + `micropip` approach with 2-3 local wheels
- Experiment 2: Scaling to 5, 10, 20 wheels
- Experiment results will determine: which loading strategy, what cache headers, what HTML generation changes

### D4: `AppConfig.wheel_mode` controls bundling strategy
```python
@dataclass
class AppConfig:
    wheel_mode: Literal["bundled", "split"] = "bundled"
```
When `wheel_mode="split"`, the build produces separate wheels for webcompy, each dependency, and the app.

### D5: Cache headers differ per wheel type in split mode
| Wheel | Dev Server | Production (SSG) |
|-------|-----------|-------------------|
| Framework | `max-age=86400, must-revalidate` | ETag by hosting |
| Dependencies | `max-age=86400, must-revalidate` | ETag by hosting |
| App (dev) | `no-cache` | N/A |
| App (SSG) | N/A | ETag by hosting |

### D6: Task plan is preliminary
Tasks will be refined based on experiment results. Do not begin implementation until experiments confirm a viable loading strategy.

## Architecture

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

SPLIT MODE (this change, opt-in):
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

## Specs Affected

- `app-config` — add `wheel_mode` field
- `cli` — add `--wheel-mode` CLI flag, multi-wheel serving
- `wheel-builder` — reintroduce `make_browser_webcompy_wheel()`, per-dependency wheel generation

## Non-goals

- This does not replace the default bundled mode.
- This does not implement per-route code splitting.
- This does not change WASM or pure-Python dependency handling.