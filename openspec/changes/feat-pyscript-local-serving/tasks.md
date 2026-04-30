# Tasks: PyScript Local Serving — Same-Origin Runtime Assets

- [ ] **Task 1: Add `runtime_serving` to AppConfig**

**Estimated time: ~0.5 hours**

### Steps

1. Add `runtime_serving: Literal["cdn", "local"] | None = None` to `AppConfig` dataclass in `webcompy/app/_config.py`. The `None` default means "unset" — resolved to `"cdn"` at build time unless `standalone=True` overrides it to `"local"` (see `feat-standalone`).
2. Add `--runtime-serving` (value argument: `local`/`cdn`) flag to `webcompy start` and `webcompy generate` subcommands in `_argparser.py`.
3. Update `_server.py` and `_generate.py` to pass the flag through.
4. Write unit tests for config dataclass.

### Acceptance Criteria

- `AppConfig(runtime_serving="local")` stores the flag.
- `--runtime-serving` CLI flag is parsed correctly and overrides `AppConfig.runtime_serving`.

---

- [ ] **Task 2: Implement runtime asset download with caching**

**Estimated time: ~1.5 hours**

### Steps

1. Create `webcompy/cli/_runtime_downloader.py`.
2. Define `PYSCRIPT_CORE_ASSETS` list: `["core.js", "core.css"]`.
3. Define `PYODIDE_RUNTIME_ASSETS` list: `["pyodide.mjs", "pyodide.asm.wasm", "pyodide.asm.js", "python_stdlib.zip", "pyodide-lock.json"]`.
4. Implement `download_runtime_assets(pyodide_version: str, pyscript_version: str, dest_dir: Path) -> dict[str, Path]`:
   - Download PyScript assets from `https://pyscript.net/releases/{pyscript_version}/{filename}`.
   - Download Pyodide runtime assets from `https://cdn.jsdelivr.net/pyodide/v{pyodide_version}/full/{filename}`.
   - Place PyScript assets in `dest_dir/` and Pyodide assets in `dest_dir/pyodide/`.
   - Cache at `~/.cache/webcompy/runtime-assets/{pyscript_version}/` (XDG-aware).
   - Verify SHA256 for Pyodide assets against `pyodide-lock.json` hashes.
5. Reuse `_pyodide_downloader.py` patterns (urllib, timeout, error handling).
6. Write unit tests with mocked HTTP.

### Acceptance Criteria

- All specified assets are downloaded to the correct subdirectories.
- Cached assets are reused without network requests.
- SHA256 hash mismatches cause errors.
- Cache follows XDG conventions.

---

- [ ] **Task 3: Update `generate_html()` for runtime-local mode**

**Estimated time: ~1 hour**

### Steps

1. Add `runtime_serving: str = "cdn"` parameter to `generate_html()`.
2. When `runtime_serving="local"`:
   - Replace `{PYSCRIPT_BASE_URL}/core.js` → `/_webcompy-assets/core.js`.
   - Replace `{PYSCRIPT_BASE_URL}/core.css` → `/_webcompy-assets/core.css`.
   - Add `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"` to py-config.
   - Add `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"` to py-config.
3. When `wasm_serving="local"` and `runtime_serving="cdn"`, set `lockFileURL` to CDN URL (interaction with `feat-wasm-local-serving`).
4. Write unit tests.

### Acceptance Criteria

- Runtime-local HTML references `/_webcompy-assets/core.js` and `/_webcompy-assets/core.css`.
- Runtime-local py-config includes `interpreter` and `lockFileURL`.
- Non-runtime-local HTML is unchanged.

---

- [ ] **Task 4: Update `generate_static_site()` and `create_asgi_app()` for runtime-local mode**

**Estimated time: ~1.5 hours**

### Steps

1. In `generate_static_site()`:
   - When `runtime_serving="local"`, call `download_runtime_assets()`.
   - Place assets in `dist/_webcompy-assets/` and `dist/_webcompy-assets/pyodide/`.
   - Configure `generate_html()` with `runtime_serving="local"`.
2. In `create_asgi_app()`:
   - When `runtime_serving="local"`, serve `/_webcompy-assets/` routes from cached assets.
3. Write integration tests.

### Acceptance Criteria

- `webcompy generate --runtime-serving local` produces all assets in `dist/_webcompy-assets/`.
- Dev server with `runtime_serving="local"` serves assets from `/_webcompy-assets/`.

---

- [ ] **Task 5: Update lock file schema for runtime serving**

**Estimated time: ~0.5 hours**

### Steps

1. Add `runtime_serving: str` field to `Lockfile` dataclass.
2. Add `runtime_assets: dict` field to `Lockfile` dataclass.
3. When `runtime_serving="local"`, populate `runtime_assets` with downloaded asset URLs and hashes.
4. When `runtime_serving="cdn"`, omit `runtime_assets` from the lock file output.
5. Write unit tests.

### Acceptance Criteria

- Lock file with `runtime_serving="local"` contains `runtime_serving: "local"` and `runtime_assets` with URLs and hashes.
- Lock file without runtime-local mode has `runtime_serving: "cdn"` and `runtime_assets` is absent from the output.

---

- [ ] **Task 6: E2E test for runtime-local mode**

**Estimated time: ~1 hour**

### Steps

1. Create E2E test that starts dev server in runtime-local mode.
2. Verify all asset URLs in generated HTML are local (starting with `/_webcompy-assets/`).
3. Verify py-config includes `interpreter` and `lockFileURL` with local paths.
4. Verify the application boots correctly in the browser.
5. Intercept network requests and assert no external CDN requests are made.

### Acceptance Criteria

- Runtime-local mode E2E test passes.
- All asset URLs in rendered HTML are local paths.
- Network request interception confirms no external CDN calls during page load.