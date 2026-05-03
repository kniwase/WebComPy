## Context

WebComPy supports `runtime_serving="local"` (standalone mode) which downloads PyScript/Pyodide runtime assets for offline use. Currently, only `core.js` and `core.css` are downloaded from the PyScript CDN. However, PyScript 2026.3.1's `core.js` is a thin entry point that dynamically imports `./core-BuLtL7jM.js`, which in turn imports 15+ additional `.js` files via relative `import()` calls. This makes standalone mode completely non-functional — PyScript initialization hangs because the browser cannot resolve these transitive dependencies.

The PyScript project provides an official `offline_{version}.zip` bundle (7.2MB) containing all necessary runtime files in a `pyscript/` directory with the correct flat structure for relative imports to resolve.

Current architecture:
- `PYSCRIPT_CORE_ASSETS = ["core.js", "core.css"]` — hardcoded, incomplete
- `download_runtime_assets()` downloads individual files from `pyscript.net/releases/{version}/{filename}`
- Downloaded files are cached in `<app_package>/.webcompy_modules/runtime-assets/{version}/`
- Files are copied to `dist/_webcompy-assets/` for SSG or served in-memory for dev server
- Lockfile records `runtime_assets` with URL and SHA256 for each file

## Goals / Non-Goals

**Goals:**
- Fix standalone mode so PyScript initializes correctly when runtime assets are served locally
- Download the complete PyScript offline bundle instead of individual files
- Preserve caching behavior (download once, serve from `modules_dir` cache)
- Maintain backward compatibility with existing lockfiles (gracefully handle old format)
- Update the lockfile to record all PyScript core bundle files

**Non-Goals:**
- Changing CDN mode (`runtime_serving="cdn"`) — continues to reference `https://pyscript.net/releases/{version}/core.js` directly
- Adding MicroPython runtime support
- Modifying PyScript itself
- Supporting fully offline first-time runs (network access required for initial download, then cached)

## Decisions

### Decision 1: Use offline ZIP instead of individual file downloads

**Choice**: Download `offline_{pyscript_version}.zip` from PyScript releases and extract the `pyscript/` directory.

**Rationale**: The offline ZIP is the official distribution format recommended by PyScript docs. It contains all transitive dependencies in the correct flat structure with relative imports that resolve correctly. Individual file downloads would require recursive dependency resolution by parsing `import()` calls in JS — fragile and version-specific.

**Alternative considered**: Parse `core.js` and recursively resolve `import()` calls. Rejected because: (1) fragile against PyScript version changes, (2) requires JS parsing logic in Python, (3) doesn't handle future dependency additions.

### Decision 2: Place PyScript core files in `_webcompy-assets/` with flat structure

**Choice**: Extract files from `pyscript/` in the zip to `_webcompy-assets/` in the output (SSG) or serve them at `/_webcompy-assets/` (dev server), preserving the flat structure so relative `import()` paths like `./core-BuLtL7jM.js` resolve correctly.

**Rationale**: The HTML already references `/_webcompy-assets/core.js` and `/_webcompy-assets/core.css`. Adding `core-BuLtL7jM.js` and other bundle files alongside them preserves the existing path convention and ensures relative imports work.

### Decision 3: Filter out unnecessary files from the offline bundle

**Choice**: Exclude `.map` source maps, `.d.ts` type definitions, `micropython/` directory, `pyodide/` directory (already handled separately), `service-worker.js`, `xterm.css`, `index.html`, and `mini-coi-fd.js`. Include only `.js` and `.css` files from the `pyscript/` directory root.

**Rationale**: The offline bundle contains ~7.2MB but many files are unnecessary for WebComPy. Source maps and type definitions add size without runtime benefit. MicroPython is not used. Pyodide files are already downloaded and placed in `_webcompy-assets/pyodide/`. The service worker and mini-coi are not needed.

### Decision 4: Cache the extracted files in `modules_dir`

**Choice**: Extract the ZIP to `modules_dir/runtime-assets/{pyscript_version}/pyscript/` cache directory. On subsequent runs, if any `.js` file beyond `core.js` exists in the cache directory (indicating the bundle was previously fully extracted), skip the download and use cached files.

**Cache detection logic**: Check if `modules_dir/runtime-assets/{pyscript_version}/pyscript/core-BuLtL7jM.js` (or any `.js` file not in the legacy `core.js`/`core.css` list) exists. If yes, the bundle was previously extracted. Read all `.js`/`.css` files (excluding `.map`, `.d.ts`) from the cache directory and compute SHA256 for each. This avoids the need for a separate metadata file.

**Rationale**: Consistent with the existing `modules_dir` caching pattern introduced by project-local-cache. Avoids re-downloading 7.2MB on every run. The existence check on a non-legacy file is a lightweight way to detect if the full bundle was previously extracted without requiring an additional metadata file.

### Decision 5: Update lockfile `runtime_assets` to include all PyScript core files

**Choice**: The lockfile `runtime_assets` dict shall contain entries for all `.js` and `.css` files from the PyScript core bundle, with filenames as keys (matching the offline zip filenames, e.g., `core-BuLtL7jM.js`, `donkey-2hW3ZLW0.js`).

**Rationale**: This enables verification that all required files are present and allows the SSG/dev server to check completeness. Old lockfiles with only `core.js` and `core.css` will be treated as stale and regenerated.

## Risks / Trade-offs

- **[Offline ZIP size ~7.2MB]** → Acceptable for standalone mode. First download is larger, but subsequent runs use cache. Users who want CDN mode are unaffected.
- **[PyScript version upgrade may change bundle structure]** → The offline ZIP approach is version-pinned. New PyScript versions may have different files, but the ZIP download approach handles this automatically.
- **[Relative import paths assume flat directory structure]** → This matches the offline ZIP structure (all files in `pyscript/` flat). As long as we preserve this structure, imports resolve correctly.
- **[Old lockfiles only have core.js/core.css]** → `resolve_lockfile()` will detect the mismatch (missing runtime_assets) and regenerate the lockfile. This is existing behavior.
- **[User-Agent header for downloads]** → Already fixed in a previous change (`WebComPy/0.1`). The ZIP download URL uses the same `pyscript.net` domain which requires this header.