# Design: WASM Local Serving — Same-Origin WASM Package Serving

## Design Decisions

### D1: WASM packages are downloaded from the Pyodide CDN at build time
WASM wheel files are downloaded from `https://cdn.jsdelivr.net/pyodide/v{version}/full/{file_name}` using the `file_name` field from `pyodide-lock.json`. They are placed in `_webcompy-assets/packages/` for SSG or served from memory in dev mode.

### D2: `py-config.packages` switches from CDN names to local URLs
In default mode: `packages = ["numpy", "matplotlib"]` (CDN names).
In WASM local serving mode: `packages = ["/_webcompy-assets/packages/numpy-2.2.5-...wasm32.whl", "/_webcompy-assets/packages/matplotlib-3.8.4-...wasm32.whl"]` (local URLs).

### D3: `lockFileURL` is always set when `wasm_serving="local"`
When WASM packages are served locally as URLs in `py-config.packages`, Pyodide uses micropip to install them. Micropip consults `pyodide-lock.json` to resolve transitive dependencies. Without `lockFileURL`, Pyodide uses its built-in lock, which may not match the Pyodide version. When `wasm_serving="local"`, `lockFileURL` SHALL be set to the Pyodide CDN URL (`https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json`). When `feat-pyscript-local-serving` is also enabled and `runtime_serving="local"`, `lockFileURL` is overridden to point to the local `pyodide-lock.json` instead.

### D4: `AppConfig.wasm_serving` controls the serving mode
```python
@dataclass
class AppConfig:
    wasm_serving: Literal["cdn", "local"] | None = None
```
When `wasm_serving` is `None` (unset), it defaults to `"cdn"`. This `None` sentinel enables the `standalone` flag to distinguish between "unset (should be overridden to `local`)" and "explicitly set to `cdn` (should be preserved)". When `wasm_serving="local"`, WASM packages are downloaded and served from the same origin.

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