# Tasks: Standalone — Orchestration Change for Complete Offline Capability

**NOTE: Tasks depend on `feat-wasm-local-serving` and `feat-pyscript-local-serving` being implemented first.**

- [ ] **Task 1: Add `standalone` flag to AppConfig**
  - Add `standalone: bool = False` to `AppConfig`.
  - Add `--standalone` CLI flag to `webcompy start` and `webcompy generate`.
  - When `standalone=True` and individual local-serving fields are at defaults, set:
    - `serve_all_deps=True` (forced with warning if explicitly set to `False`)
    - `wasm_serving="local"` (default, can be overridden to `"cdn"`)
    - `runtime_serving="local"` (default, can be overridden to `"cdn"`)
  - Add `--no-standalone` CLI flag.
  - Write unit tests for config precedence.

- [ ] **Task 2: Implement standalone orchestration logic**
  - When `standalone=True`, compute effective config values:
    - If `wasm_serving` is `None` (unset), override to `"local"`. If explicitly `"cdn"`, preserve it.
    - If `runtime_serving` is `None` (unset), override to `"local"`. If explicitly `"cdn"`, preserve it.
    - `serve_all_deps` is forced to `True` (warning if explicitly `False` with `standalone=True`).
  - Pass effective config to downstream logic (WASM download, runtime download, CDN deps download).
  - Write unit tests for orchestration behavior and edge cases.

- [ ] **Task 3: Add `standalone` field to lock file**
  - Add `standalone: bool` field to `Lockfile` dataclass.
  - When `standalone=True`, the lock file records `standalone: true`.
  - The lock file does NOT need a separate `standalone_assets` section — `wasm_serving`, `runtime_serving`, and `runtime_assets` already capture all asset information.
  - Write unit tests.

- [ ] **Task 4: Update generate_static_site and create_asgi_app for standalone mode**
  - In `generate_static_site()`: when `standalone=True`, orchestrate all asset downloads:
    - Download PyScript runtime + Pyodide runtime (via runtime download logic).
    - Download WASM package wheels (via WASM download logic).
    - Download CDN pure-Python packages and bundle (via CDN download logic).
    - Place all assets in `dist/_webcompy-assets/` and `dist/_webcompy-assets/packages/`.
    - Generate HTML with all local URLs.
  - In `create_asgi_app()`: when `standalone=True`, serve all assets from `/_webcompy-assets/`.
  - Write integration tests.

- [ ] **Task 5: E2E test for standalone mode**
  - Start dev server in standalone mode.
  - Verify all asset URLs in generated HTML are local (no external CDN URLs).
  - Verify `py-config` includes `interpreter` and `lockFileURL` pointing to local paths.
  - Verify the application boots correctly in the browser.
  - Intercept network requests and assert no external CDN requests are made.