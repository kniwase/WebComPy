## ADDED Requirements

### Requirement: The CLI shall serve local assets from disk in dev server mode
When `runtime_serving="local"` or `wasm_serving="local"`, the dev server SHALL serve runtime and WASM assets directly from the project-local cache using `FileResponse` or equivalent disk-based streaming, rather than loading file contents into memory.

#### Scenario: Serving runtime assets from disk
- **WHEN** a browser requests `/_webcompy-assets/core.js` with `runtime_serving="local"`
- **THEN** the server SHALL stream the file from `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/core.js`
- **AND** the file SHALL NOT be fully loaded into memory before the response begins

#### Scenario: Serving WASM wheels from disk
- **WHEN** a browser requests `/_webcompy-assets/packages/{file_name}` with `wasm_serving="local"`
- **THEN** the server SHALL stream the file from `{app_package_path}/.webcompy_modules/pyodide-packages/{pyodide_version}/{file_name}`
- **AND** the file SHALL NOT be fully loaded into memory before the response begins

## MODIFIED Requirements

### Requirement: The CLI shall download pure-Python packages from Pyodide CDN when serve_all_deps is True
When `serve_all_deps=True`, the CLI SHALL download pure-Python package wheels from the Pyodide CDN, verify their SHA256 hashes against the lock file, cache them locally in the project-local cache, extract them, and bundle them into the app wheel.

#### Scenario: Downloading and bundling CDN packages
- **WHEN** a developer runs `python -m webcompy start --dev` with `serve_all_deps=True`
- **AND** the lock file contains pure-Python packages with `in_pyodide_cdn=True`
- **THEN** those packages SHALL be downloaded from the Pyodide CDN
- **AND** their SHA256 hashes SHALL be verified against the lock file
- **AND** the wheels SHALL be extracted and bundled into the app wheel
- **AND** downloaded wheels SHALL be cached at `{app_package_path}/.webcompy_modules/pyodide-packages/{pyodide_version}/`

#### Scenario: Cache hit
- **WHEN** a previously downloaded wheel exists in the project-local cache with a matching SHA256 hash
- **THEN** the download SHALL be skipped
- **AND** the cached wheel SHALL be used

### Requirement: The CLI shall download and serve PyScript/Pyodide runtime assets locally when runtime_serving is local
When `runtime_serving="local"`, the CLI SHALL download PyScript core assets and Pyodide runtime assets at build time and serve them from the same origin. Runtime assets SHALL be cached in the project-local cache directory and reused across builds.

#### Scenario: Generating a static site with local runtime serving
- **WHEN** a developer runs `python -m webcompy generate` with `AppConfig(runtime_serving="local")`
- **THEN** PyScript core assets SHALL be copied from `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/` to `dist/_webcompy-assets/`
- **AND** Pyodide runtime assets SHALL be copied from `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/pyodide/` to `dist/_webcompy-assets/pyodide/`
- **AND** the generated HTML SHALL reference local asset URLs instead of CDN URLs

#### Scenario: Starting the dev server with local runtime serving
- **WHEN** a developer runs `python -m webcompy start --dev` with `AppConfig(runtime_serving="local")`
- **THEN** the dev server SHALL serve PyScript core assets from `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/`
- **AND** the dev server SHALL serve Pyodide runtime assets from `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/pyodide/`
- **AND** the generated HTML SHALL reference local asset URLs

#### Scenario: Runtime assets are cached locally
- **WHEN** a developer runs `webcompy generate` or `webcompy start` with `runtime_serving="local"`
- **THEN** downloaded runtime assets SHALL be cached at `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/`
- **AND** cached assets with matching versions SHALL be reused without network requests

### Requirement: Temporary directories used for runtime asset downloads SHALL be cleaned up
When `webcompy generate` or `webcompy start` creates temporary directories for runtime asset downloads, those directories SHALL be cleaned up after use. Note: this requirement primarily applies to CDN pure-Python wheel extraction for bundling; runtime and WASM assets no longer use temporary directories.

#### Scenario: Temporary directory cleanup after CDN wheel extraction
- **WHEN** `webcompy generate` or `webcompy start` with `serve_all_deps=True` completes
- **AND** CDN pure-Python wheels were extracted for bundling
- **THEN** any temporary directories created for wheel extraction SHALL be removed

## REMOVED Requirements

### Requirement: Temporary directory cleanup after static site generation and dev server shutdown for runtime assets
**Reason**: Runtime and WASM assets are now served directly from the project-local cache (`.webcompy_modules/`), eliminating the need for temporary directories.
**Migration**: No action required. The `.webcompy_modules/` directory persists across builds for caching.
