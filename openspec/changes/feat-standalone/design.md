# Design: Standalone — Orchestration Change for Complete Offline PWA Support

## Design Decisions

### D1: `standalone` is a convenience toggle that enables all local-serving modes
`standalone=True` is equivalent to setting `deps_serving="local-cdn"` + `wasm_serving="local"` + runtime local serving. It exists as a single config option for developers who want complete offline capability without configuring each level individually.

### D2: Individual local-serving configs take precedence
If `standalone=True` but individual config options are explicitly set, the individual options take precedence. This allows fine-grained control when needed.

### D3: Asset download orchestration
When `standalone=True`, the CLI orchestrates downloads from all three local-serving changes:
- PyScript runtime assets (`feat-pyscript-local-serving`)
- WASM package wheels (`feat-wasm-local-serving`)
- Pure-Python package wheels (`feat-deps-local-serving`)

### D4: Task planning is preliminary
This change depends on `feat-deps-local-serving`, `feat-wasm-local-serving`, and `feat-pyscript-local-serving`. The tasks below are preliminary and will be revised based on implementation experience from prerequisite changes.

## Architecture

```
standalone=True equivalent config:
  AppConfig(
      deps_serving="local-cdn",   # feat-deps-local-serving
      wasm_serving="local",         # feat-wasm-local-serving
      runtime_local=True,            # feat-pyscript-local-serving
  )

Complete offline build output:
  dist/
  ├── _webcompy-assets/
  │   ├── core.js, core.css                          (PyScript)
  │   ├── pyodide.mjs, pyodide.asm.wasm, ...         (Pyodide)
  │   ├── pyodide-lock.json                           (Pyodide)
  │   └── packages/
  │       └── numpy-2.2.5-...wasm32.whl              (WASM)
  ├── _webcompy-app-package/
  │   └── myapp-py3-none-any.whl                     (webcompy + app + 純Py)
  └── index.html (all local URLs, zero external requests)
```

## Specs Affected

- `app-config` — add `standalone` flag
- `cli` — orchestrate all local-serving modes
- `lockfile` — coordinate `standalone_assets` from all three changes