# Tasks: PyScript Local Serving — Same-Origin Runtime Assets

- [ ] **Task 1: Add "runtime_serving" flag to `ServerConfig` and `GenerateConfig`**

**Estimated time: ~0.5 hours**

### Steps

1. Add `local-serving: bool = False` to `ServerConfig` dataclass in `webcompy/app/_config.py`.
2. Add `local-serving: bool = False` to `GenerateConfig` dataclass.
3. Add `--runtime-serving` flag to `webcompy start` and `webcompy generate` subcommands in `_argparser.py`.
4. Update `_server.py` and `_generate.py` to pass the flag through.
5. Write unit tests for config dataclass.

### Acceptance Criteria

- `ServerConfig(runtime_serving="local")` stores the flag.
- `GenerateConfig(runtime_serving="local")` stores the flag.
- `--runtime-serving` CLI flag is parsed correctly.

---

- [ ] **Task 2: Implement asset download logic**

**Estimated time: ~1 hour**

### Steps

1. Create `webcompy/cli/_runtime_assets.py`.
2. Define `PYSCRIPT_ASSETS` dict mapping asset names to URL templates.
3. Define `PYODIDE_RUNTIME_ASSETS` dict for runtime files (`pyodide.mjs`, `pyodide.asm.wasm`, `pyodide.asm.js`, `python_stdlib.zip`).
4. Implement `download_runtime_assets(pyodide_version, pyscript_version, dest_dir, lockfile)`:
   - Download each PyScript asset from CDN.
   - Download each Pyodide runtime asset from CDN.
   - Download each Pyodide package wheel from CDN (using lock file's `pyodide_packages` entries).
   - Copy to `dest_dir/_webcompy-assets/`.
5. Write unit tests with mocked HTTP.

### Acceptance Criteria

- All specified assets are downloaded to the target directory.
- Non-existent assets cause clear error messages.

---

- [ ] **Task 3: Implement asset caching and verification**

**Estimated time: ~1 hour**

### Steps

1. Implement `cache_dir()` returning `~/.cache/webcompy/assets/` (XDG-aware).
2. Implement `download_with_cache(url, cache_key, dest_dir)`:
   - Check cache directory first. If cached, copy and return.
   - Otherwise, download from CDN, save to cache, and copy to `dest_dir`.
   - Cache key includes version to avoid stale assets.
3. Implement SHA256 hash verification against `pyodide-lock.json` hashes.
   - For Pyodide packages, use the `sha256` field from the lock.
   - For runtime assets, verify against known hashes or skip if unavailable.
4. Write unit tests.

### Acceptance Criteria

- Cached assets are reused without network requests.
- SHA256 hash mismatches cause errors.
- Cache follows XDG conventions.

---

- [ ] **Task 4: Update `generate_html()` for runtime-local mode**

**Estimated time: ~1 hour**

### Steps

1. Add `local-serving: bool = False` parameter to `generate_html()`.
2. When `runtime_serving="local"`:
   - Replace `PYSCRIPT_BASE_URL/core.js` → `/_webcompy-assets/core.js`.
   - Replace `PYSCRIPT_BASE_URL/core.css` → `/_webcompy-assets/core.css`.
   - Add `lockFileURL` to PyScript config: `/_webcompy-assets/pyodide-lock.json`.
   - Pyodide package URLs → `/_webcompy-assets/packages/{filename}`.
3. Write unit tests.

### Acceptance Criteria

- Runtime-local HTML references `/_webcompy-assets/core.js`.
- Runtime-local HTML includes `lockFileURL` in PyScript config.
- Non-local-serving HTML is unchanged.

---

- [ ] **Task 5: Update `generate_static_site()` and `create_asgi_app()` for local-serving**

**Estimated time: ~1.5 hours**

### Steps

1. In `generate_static_site()`:
   - When `runtime_serving="local"`, call `download_runtime_assets()`.
   - Configure `generate_html()` with `runtime_serving="local"`.
2. In `create_asgi_app()`:
   - When `runtime_serving="local"`, serve `/_webcompy-assets/` routes from cached assets.
3. Write integration tests.

### Acceptance Criteria

- `webcompy generate --runtime-serving` produces all assets in `dist/_webcompy-assets/`.
- Dev server with `runtime_serving="local"` serves assets from `/_webcompy-assets/`.

---

- [ ] **Task 6: Update lock file schema for local-serving assets**

**Estimated time: ~0.5 hours**

### Steps

1. Add `runtime_assets` field to `Lockfile` dataclass.
2. When `runtime_serving="local"`, populate with downloaded asset URLs and hashes.
3. When `runtime_serving="cdn"`, leave as empty dict.
4. Write unit tests.

### Acceptance Criteria

- Lock file with `runtime_serving="local"` contains asset URLs and hashes.
- Lock file without runtime-local mode has empty `runtime_assets`.

---

- [ ] **Task 7: E2E test for runtime-local mode**

**Estimated time: ~1 hour**

### Steps

1. Create E2E test that starts dev server in runtime-local mode.
2. Verify all asset URLs in generated HTML are local (starting with `/_webcompy-assets/`).
3. Verify PyScript config references local URLs.
4. Verify the application boots correctly in the browser.
5. Intercept network requests and assert no external CDN requests are made (use Playwright's route interception to verify all requests go to localhost).

### Acceptance Criteria

- Runtime-local mode E2E test passes.
- All asset URLs in rendered HTML are local paths.
- Network request interception confirms no external CDN calls during page load.