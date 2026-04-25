# Design: WASM Local Serving — Same-Origin WASM Package Serving

## Design Decisions

### D1: WASM packages are downloaded from the Pyodide CDN at build time
WASM wheel files are downloaded from `https://cdn.jsdelivr.net/pyodide/v{version}/full/{file_name}` using the `file_name` field from `pyodide-lock.json`. They are placed in `_webcompy-assets/packages/` for SSG or served from memory in dev mode.

### D2: `py-config.packages` switches from CDN names to local URLs
In default mode: `packages = ["numpy", "matplotlib"]` (CDN names).
In WASM local serving mode: `packages = ["/_webcompy-assets/packages/numpy-2.2.5-...wasm32.whl", "/_webcompy-assets/packages/matplotlib-3.8.4-...wasm32.whl"]` (local URLs).

### D3: `lockFileURL` may be required for local WASM serving
When WASM packages are served locally, PyScript/micropip needs `pyodide-lock.json` to resolve dependencies between WASM packages. This requires setting `lockFileURL` in `py-config`, which is handled by `feat-pyscript-local-serving`. For `feat-wasm-local-serving` alone, `lockFileURL` may be set to the Pyodide CDN URL or a local path.

### D4: `AppConfig.wasm_serving` controls the serving mode
```python
@dataclass
class AppConfig:
    wasm_serving: Literal["cdn", "local"] = "cdn"
```
When `wasm_serving="cdn"` (default), WASM packages are loaded from the Pyodide CDN. When `wasm_serving="local"`, WASM packages are downloaded and served from the same origin.

## Architecture

```
DEFAULT MODE:
  Pyodide CDN ─────── numpy (WASM via packages name)
  py-config.packages = ["numpy"]

WASM LOCAL SERVING:
  WebComPy server ─── /_webcompy-assets/packages/numpy-2.2.5-...wasm32.whl
  py-config.packages = ["/_webcompy-assets/packages/numpy-2.2.5-...wasm32.whl"]
```

## Specs Affected

- `app-config` — add `wasm_serving` field
- `cli` — download WASM wheels, serve from local paths
- `lockfile` — add `wasm_serving` field