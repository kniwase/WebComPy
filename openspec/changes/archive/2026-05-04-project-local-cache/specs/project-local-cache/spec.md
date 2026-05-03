# Project-Local Cache

## Purpose

WebComPy's standalone mode (local serving of runtime and WASM assets) requires downloading large files from Pyodide/PyScript CDNs. Rather than storing these in a global cache outside the project directory, each application package should maintain its own isolated cache. This improves project isolation, makes cache state visible to the user, and enables efficient disk-based serving instead of loading all assets into memory.

## Requirements

### Requirement: The CLI shall maintain a project-local cache directory
Each WebComPy application package SHALL have its own cache directory at `{app_package_path}/.webcompy_modules/`. This directory SHALL be automatically created on first use and SHALL contain a `.gitignore` file with `*` so its contents are never tracked by version control.

#### Scenario: First dev server start creates .webcompy_modules
- **WHEN** a developer runs `python -m webcompy start --dev --runtime-serving local` for the first time
- **THEN** `{app_package_path}/.webcompy_modules/` SHALL be created if it does not exist
- **AND** `{app_package_path}/.webcompy_modules/.gitignore` SHALL be created with content `*`
- **AND** downloaded runtime assets SHALL be stored in `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/`

#### Scenario: First static site generation creates .webcompy_modules
- **WHEN** a developer runs `python -m webcompy generate --runtime-serving local` for the first time
- **THEN** `{app_package_path}/.webcompy_modules/` SHALL be created if it does not exist
- **AND** `{app_package_path}/.webcompy_modules/.gitignore` SHALL be created with content `*`

#### Scenario: .webcompy_modules is not tracked by git
- **WHEN** a developer runs `git status` in a project where `.webcompy_modules/` has been created
- **THEN** `.webcompy_modules/` SHALL NOT appear as an untracked directory
- **AND** files inside `.webcompy_modules/` SHALL NOT appear as untracked files

### Requirement: The CLI shall store downloaded wheels in the project-local cache
WASM wheels and CDN pure-Python wheels downloaded from the Pyodide CDN SHALL be stored in `{app_package_path}/.webcompy_modules/pyodide-packages/{pyodide_version}/`. The existing SHA256 verification and cache-hit logic SHALL be preserved.

#### Scenario: Downloading a WASM wheel
- **WHEN** a developer runs `python -m webcompy start --dev --wasm-serving local`
- **AND** the lock file contains a WASM package entry with `file_name` and `sha256`
- **THEN** the wheel SHALL be downloaded to `{app_package_path}/.webcompy_modules/pyodide-packages/{pyodide_version}/{file_name}`
- **AND** subsequent starts SHALL reuse the cached wheel if SHA256 matches

#### Scenario: Downloading a CDN pure-Python wheel
- **WHEN** a developer runs `python -m webcompy start --dev` with `serve_all_deps=True`
- **AND** the lock file contains a pure-Python package with `in_pyodide_cdn=True`
- **THEN** the wheel SHALL be downloaded to `{app_package_path}/.webcompy_modules/pyodide-packages/{pyodide_version}/{file_name}`
- **AND** subsequent starts SHALL reuse the cached wheel if SHA256 matches

### Requirement: The CLI shall store runtime assets in the project-local cache
PyScript core assets (`core.js`, `core.css`) and Pyodide runtime assets (`pyodide.mjs`, `pyodide.asm.wasm`, etc.) SHALL be stored in `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/` and its `pyodide/` subdirectory. Cached assets SHALL be reused on subsequent builds without network requests.

#### Scenario: Downloading runtime assets
- **WHEN** a developer runs `python -m webcompy generate --runtime-serving local`
- **THEN** PyScript core assets SHALL be downloaded to `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/`
- **AND** Pyodide runtime assets SHALL be downloaded to `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/pyodide/`
- **AND** subsequent runs SHALL reuse cached assets without downloading

### Requirement: The dev server shall serve runtime and WASM assets from disk
When `runtime_serving="local"` or `wasm_serving="local"`, the dev server SHALL serve assets directly from the project-local cache directory using `FileResponse` (or equivalent disk-based streaming), rather than loading file contents into memory with `read_bytes()`.

#### Scenario: Serving a local runtime asset
- **WHEN** a browser requests `/_webcompy-assets/core.js`
- **AND** `runtime_serving="local"`
- **THEN** the server SHALL stream the file from `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/core.js`
- **AND** the file SHALL NOT be fully loaded into memory before the response begins

#### Scenario: Serving a local WASM wheel
- **WHEN** a browser requests `/_webcompy-assets/packages/{file_name}`
- **AND** `wasm_serving="local"`
- **THEN** the server SHALL stream the file from `{app_package_path}/.webcompy_modules/pyodide-packages/{pyodide_version}/{file_name}`
- **AND** the file SHALL NOT be fully loaded into memory before the response begins

### Requirement: Static site generation shall copy from project-local cache to dist
During `webcompy generate`, runtime assets and WASM wheels SHALL be copied directly from `.webcompy_modules/` to the output `dist/_webcompy-assets/` directory. No temporary directories SHALL be created for this purpose.

#### Scenario: Generating with local runtime serving
- **WHEN** a developer runs `python -m webcompy generate --runtime-serving local`
- **THEN** runtime assets SHALL be copied from `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/` to `dist/_webcompy-assets/`
- **AND** no temporary directory SHALL be created for runtime asset staging

#### Scenario: Generating with local WASM serving
- **WHEN** a developer runs `python -m webcompy generate --wasm-serving local`
- **THEN** WASM wheels SHALL be copied from `{app_package_path}/.webcompy_modules/pyodide-packages/{pyodide_version}/` to `dist/_webcompy-assets/packages/`
- **AND** no temporary directory SHALL be created for wheel staging

### Requirement: The global home directory cache SHALL no longer be used
The CLI SHALL NOT write to or read from `~/.cache/webcompy/` (or `XDG_CACHE_HOME/webcompy/`). All download caching SHALL use the project-local `.webcompy_modules/` directory exclusively.

#### Scenario: Fresh machine with no ~/.cache/webcompy
- **WHEN** a developer runs `python -m webcompy start --dev --runtime-serving local` on a machine without `~/.cache/webcompy/`
- **THEN** the build SHALL succeed
- **AND** `~/.cache/webcompy/` SHALL NOT be created
- **AND** all downloaded files SHALL be stored in `{app_package_path}/.webcompy_modules/`

#### Scenario: Existing ~/.cache/webcompy is ignored
- **WHEN** a developer has an existing `~/.cache/webcompy/` with cached assets from a previous version
- **AND** runs `python -m webcompy start --dev --runtime-serving local`
- **THEN** the existing global cache SHALL NOT be consulted
- **AND** assets SHALL be downloaded fresh into `.webcompy_modules/` if not already present there
