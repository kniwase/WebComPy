# Tasks: WASM Local Serving — Same-Origin WASM Package Serving

- [ ] **Task 1: Add `wasm_serving` to AppConfig**
  - Add `wasm_serving: Literal["cdn", "local"] = "cdn"` to `AppConfig`.
  - Add `--wasm-serving` CLI flag.
  - Write unit tests.

- [ ] **Task 2: Implement WASM wheel download with caching**
  - Download WASM wheel files from `https://cdn.jsdelivr.net/pyodide/v{version}/full/{file_name}`.
  - Cache at `~/.cache/webcompy/pyodide-packages/`.
  - Verify SHA256 hashes from `pyodide-lock.json`.
  - Write unit tests.

- [ ] **Task 3: Update lock file for `wasm_serving`**
  - Add `wasm_serving` field to `Lockfile` dataclass.
  - Include download URLs in `pyodide_packages` entries.
  - Write unit tests.

- [ ] **Task 4: Update `generate_html()` for local WASM URLs**
  - When `wasm_serving="local"`, replace CDN package names with local wheel URLs in `py-config.packages`.
  - Include `lockFileURL` pointing to local `pyodide-lock.json` (or CDN URL).
  - Write unit tests.

- [ ] **Task 5: Update server and SSG for WASM local serving**
  - Serve WASM wheels from `/_webcompy-assets/packages/` in dev mode.
  - Copy WASM wheels to `dist/_webcompy-assets/packages/` in SSG mode.
  - Set appropriate cache headers.
  - Write integration tests.