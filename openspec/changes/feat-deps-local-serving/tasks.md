# Tasks: Deps Local Serving — Same-Origin Pure-Python Package Serving

**NOTE: Implementation depends on `feat-dependency-bundling` being complete. Tasks are preliminary.**

- [ ] **Task 1: Add `deps_serving` to AppConfig**
  - Add `deps_serving: Literal["bundled", "local-cdn"] = "bundled"` to `AppConfig`.
  - Add `--deps-serving` CLI flag.
  - Write unit tests.

- [ ] **Task 2: Implement Pyodide CDN wheel download with caching**
  - Create download and cache mechanism for pure-Python wheel files from the Pyodide CDN.
  - Use URLs from `pyodide-lock.json` `file_name` fields.
  - Cache at `~/.cache/webcompy/pyodide-packages/`.
  - Write unit tests.

- [ ] **Task 3: Implement transitive resolution via Pyodide lock `depends` field**
  - Enhance `classify_dependencies()` to walk `depends` recursively when `deps_serving="local-cdn"`.
  - Use `importlib.metadata` as fallback for packages not in the lock.
  - Write unit tests.

- [ ] **Task 4: Extract and bundle downloaded wheels**
  - Download wheel files, extract into the app wheel content.
  - Update `make_webcompy_app_package()` to accept downloaded package directories.
  - Write unit tests.

- [ ] **Task 5: Update lock file schema for `downloaded_packages`**
  - Add `downloaded_packages` section to lock file.
  - Record URLs and SHA256 hashes for reproducibility.
  - Write unit tests.

- [ ] **Task 6: Update server and SSG for `deps_serving="local-cdn"`**
  - Integrate download logic into `create_asgi_app()` and `generate_static_site()`.
  - Pass `pyodide_package_names` (WASM only) to HTML generation.
  - Write integration tests.