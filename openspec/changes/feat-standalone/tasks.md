# Tasks: Standalone — Orchestration Change for Complete Offline PWA Support

**NOTE: Tasks are preliminary and will be revised based on implementation experience from prerequisite changes (`feat-deps-local-serving`, `feat-wasm-local-serving`, `feat-pyscript-local-serving`). Do not begin implementation until prerequisites are complete.**

- [ ] **Task 1: Add `standalone` flag to `ServerConfig` and `GenerateConfig`**
  - Add `standalone: bool = False` to both `ServerConfig` and `GenerateConfig`.
  - Add `--standalone` CLI flag to `webcompy start` and `webcompy generate`.
  - When `standalone=True`, set `deps_serving="local-cdn"`, `wasm_serving="local"`, and enable runtime local serving.
  - Individual config options take precedence over `standalone` defaults.
  - Write unit tests.

- [ ] **Task 2: Orchestrate asset downloads**
  - Coordinate downloads from `feat-pyscript-local-serving`, `feat-wasm-local-serving`, and `feat-deps-local-serving`.
  - Download PyScript runtime, Pyodide runtime, WASM packages, and pure-Python packages.
  - Place all assets in `dist/_webcompy-assets/` for SSG.
  - Serve from `/_webcompy-assets/` in dev mode.
  - Write integration tests.

- [ ] **Task 3: Update lock file for standalone_assets**
  - Add `standalone_assets` section to `Lockfile` dataclass.
  - Record PyScript/Pyodide runtime asset URLs and SHA256 hashes.
  - Write unit tests.

- [ ] **Task 4: E2E test for standalone mode**
  - Start dev server in standalone mode.
  - Verify all asset URLs in generated HTML are local.
  - Verify the application boots correctly in the browser.
  - Intercept network requests and assert no external CDN requests.