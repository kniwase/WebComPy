# Tasks: Standalone — Orchestration Change for Complete Offline PWA Support

**NOTE: Tasks are preliminary and will be revised based on implementation experience from prerequisite changes (`feat-deps-local-serving`, `feat-wasm-local-serving`, `feat-pyscript-local-serving`). Do not begin implementation until prerequisites are complete.**

- [ ] **Task 1: Add `standalone` flag to `AppConfig`**
  - Add `standalone: bool = False` to `AppConfig`.
  - Add `--standalone` CLI flag to `webcompy start` and `webcompy generate`. When set, it populates equivalent `AppConfig` settings and triggers all local-serving downloads.
  - When `standalone=True`, the default values of `deps_serving`, `wasm_serving`, and runtime serving are all set to their local modes. Individual config options already set on `AppConfig` take precedence over this default.
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