# CLI

## Purpose

The command-line interface bridges the gap between development and deployment. It provides three essential capabilities: a development server for live iteration, a static site generator for production deployment, and project scaffolding for starting new applications. These tools handle the complexity of packaging Python code for browser execution, serving it during development, and producing deployable output — tasks that are unique to a framework that runs Python in the browser.

## Requirements

### Requirement: The dev server shall serve the application with hot-reload
The development server SHALL be startable via `python -m webcompy start --dev` or `run_server(app)`. Both SHALL start a Starlette+uvicorn server that serves the application with SSE-based hot-reload. Dev mode is determined by `ServerConfig.dev` or the `--dev` CLI flag (which overrides the config file value).

#### Scenario: Starting dev server via CLI
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL start with hot-reload enabled
- **AND** `ServerConfig.dev` SHALL be overridden to `True`

#### Scenario: Starting dev server via run_server(app)
- **WHEN** a developer calls `run_server(app)` with a `WebComPyApp` instance
- **THEN** the server SHALL start with hot-reload enabled if the `--dev` CLI flag is set
- **AND** `AppConfig` from the app instance SHALL be used

#### Scenario: Starting dev server with custom port
- **WHEN** a developer runs `python -m webcompy start --port 3000`
- **THEN** the server SHALL start on port 3000
- **AND** the `--port` flag SHALL override `ServerConfig.port`

### Requirement: The dev server shall serve a single bundled wheel
The dev server SHALL build a single Python wheel containing the webcompy framework (excluding `webcompy/cli/`), application code, and appropriate pure-Python dependencies based on `serve_all_deps`. When `serve_all_deps=True`, ALL pure-Python dependencies are bundled. When `serve_all_deps=False`, only pure-Python dependencies NOT available from the Pyodide CDN are bundled; CDN-available ones are loaded by name via `py-config.packages`. The wheel SHALL be served at a stable `/_webcompy-app-package/` endpoint. The app wheel in dev mode SHALL have `Cache-Control: no-cache`.

#### Scenario: Starting the dev server with serve_all_deps=True
- **WHEN** a developer runs `python -m webcompy start --dev` with `serve_all_deps=True` (default)
- **THEN** the server SHALL build a single wheel containing webcompy (excl. cli), app code, and ALL pure-Python dependencies
- **AND** `py-config.packages` SHALL contain only the app wheel URL and WASM package names
- **AND** CDN-downloaded pure-Python packages SHALL be included in the wheel
- **AND** the wheel SHALL be served at `/_webcompy-app-package/{filename}` where `{filename}` matches the wheel URL in the generated HTML
- **AND** the browser SHALL be able to import both `webcompy` and the application package

#### Scenario: Starting the dev server with serve_all_deps=False
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **THEN** the server SHALL build a single wheel containing webcompy (excl. cli), app code, and locally-bundled dependencies only
- **AND** `py-config.packages` SHALL contain the app wheel URL, WASM package names, AND CDN pure-Python package names

#### Scenario: Dev server with assets
- **WHEN** a developer configures `assets={"logo": "images/logo.png"}` in `AppConfig`
- **THEN** the bundled wheel SHALL include the matching asset files inside the package tree
- **AND** an `_assets_registry.py` module SHALL be generated in the app package mapping `"logo"` to its package path
- **AND** `load_asset("logo")` SHALL return the file content as `bytes`

### Requirement: The generate command shall produce deployable static files
Static site generation SHALL be available via `python -m webcompy generate` or `generate_static_site(app, generate_config=None)`. Both SHALL produce a complete static site in the configured output directory. The SSG process SHALL enter the app's DI scope for the entire generation pipeline to ensure `inject()` calls during route rendering succeed. A single bundled wheel SHALL be placed in `dist/_webcompy-app-package/`.

#### Scenario: Generating a multi-page application with history mode
- **WHEN** routes are defined with history mode
- **THEN** an `index.html` SHALL be generated for each route path
- **AND** a `404.html` SHALL be generated for unmatched paths
- **AND** a single bundled wheel SHALL be placed in `dist/_webcompy-app-package/`
- **AND** the generated HTML SHALL reference the single wheel URL plus WASM-only Pyodide CDN package names
- **AND** static files SHALL be copied from the configured directory
- **AND** a `.nojekyll` file SHALL be created for GitHub Pages compatibility

#### Scenario: Generating a single-page application with hash mode
- **WHEN** no router or hash mode is used
- **THEN** a single `index.html` SHALL be generated at the dist root
- **AND** all other assets SHALL be included as in the history mode case

#### Scenario: Generating with custom dist via --dist flag
- **WHEN** a developer runs `python -m webcompy generate --dist out`
- **THEN** static files SHALL be generated in the `out` directory
- **AND** the `--dist` flag SHALL override `GenerateConfig.dist`

#### Scenario: Generating via generate_static_site(app)
- **WHEN** a developer calls `generate_static_site(app)` with a `WebComPyApp` instance
- **THEN** a static site SHALL be generated in the `dist` directory
- **AND** all routes, app packages, and static files SHALL be included

### Requirement: The init command shall scaffold a new project
Running `python -m webcompy init` SHALL create the necessary project structure including a bootstrap file, static directory, and two configuration files (`webcompy_config.py` and `webcompy_server_config.py`).

#### Scenario: Scaffolding a new project
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** template files SHALL be copied to the current directory
- **AND** a `static/` directory with `__init__.py` SHALL be created
- **AND** `webcompy_config.py` SHALL be created with `app_import_path` and `app_config`
- **AND** `webcompy_server_config.py` SHALL be created with `server_config` and `generate_config`

### Requirement: Application configuration shall be discovered via two-file pattern
The CLI SHALL discover the app instance using `webcompy_config.py` (which contains `app_import_path` and `app_config`) or the `--app` CLI flag. Configuration files can be placed at the project root or inside the app package directory. When `--app` is provided, the CLI derives the package from the import path and searches for `webcompy_server_config.py` in that package first, then falls back to the project root. The `webcompy_server_config.py` file is optional and contains server/SSG-only settings (`server_config`, `generate_config`). The `discover_app` function SHALL be the public API for programmatic app discovery, exported from `webcompy.cli`. It SHALL return a tuple of `(WebComPyApp, str | None)` where the second element is the derived package name.

#### Scenario: Discovery via --app flag
- **WHEN** a developer runs `python -m webcompy start --app my_app.bootstrap:app`
- **THEN** the CLI SHALL import `my_app.bootstrap` and use the `app` attribute
- **AND** the CLI SHALL derive the package as `"my_app"`
- **AND** `webcompy_config.py` SHALL NOT be required
- **AND** `webcompy_server_config.py` SHALL be searched first as `my_app.webcompy_server_config`, then as root-level `webcompy_server_config`

#### Scenario: Discovery via root-level webcompy_config.py
- **WHEN** a developer runs `python -m webcompy start` without `--app`
- **AND** `webcompy_config.py` exists at the project root with `app_import_path = "my_app.bootstrap:app"`
- **THEN** the CLI SHALL import `my_app.bootstrap` and get the `app` attribute

#### Scenario: No app_import_path and no --app flag
- **WHEN** a developer runs `python -m webcompy start` without `--app`
- **AND** no `webcompy_config.py` exists at the project root or it has no `app_import_path`
- **THEN** a clear error SHALL be raised indicating that either `--app` or `webcompy_config.py` with `app_import_path` is required

### Requirement: Generated HTML shall include PyScript bootstrapping
Every generated HTML page SHALL include PyScript v2026.3.1 CSS and JS, a loading screen, the app div (either pre-rendered or hidden), and a PyScript configuration specifying all required Python packages. The configuration SHALL reference a single bundled wheel (not separate framework and application wheels) and SHALL NOT include `typing_extensions` as a dependency. The bundled wheel URL SHALL use the content-hashed filename returned by `make_webcompy_app_package()`. When `AppConfig.profile=True`, the generated `<script type="py">` tag SHALL include inline profiling code that captures `pyscript_ready` at the start of PyScript execution and passes it to the app instance before `app.run()`. The PyScript configuration SHALL include `interpreter` and `lockFileURL` fields when `runtime_serving="local"`. When `runtime_serving="cdn"` (default), these fields SHALL NOT be included. When `wasm_serving="local"` and `runtime_serving="cdn"`, `lockFileURL` SHALL be set to the CDN `pyodide-lock.json` URL.

#### Scenario: Inspecting generated HTML
- **WHEN** a generated `index.html` is examined for an app package named `myapp`
- **THEN** it SHALL contain a `<script type="module">` tag loading PyScript
- **AND** a `<script type="py">` tag with the bootstrap code
- **AND** a `<style>` tag with scoped component CSS
- **AND** a loading screen div with `id="webcompy-loading"`
- **AND** the loading screen overlay SHALL use a semi-transparent dark background (e.g., `rgba(0, 0, 0, 0.5)`) so that pre-rendered content remains visible beneath during hydration
- **AND** when prerendering is enabled, the `#webcompy-app` div SHALL NOT have a `hidden` attribute
- **AND** when prerendering is disabled, the `#webcompy-app` div SHALL have a `hidden` attribute
- **AND** the PyScript packages list SHALL reference a single bundled wheel URL using the content-hashed filename from `make_webcompy_app_package()`
- **AND** `typing_extensions` SHALL NOT appear in the packages list

#### Scenario: Inspecting generated HTML with profiling enabled
- **WHEN** `AppConfig.profile=True` and a generated `index.html` is examined
- **THEN** the `<script type="py">` tag SHALL start with `import time` and `_pyscript_ready = time.perf_counter()`
- **AND** after the app import, `app._profile_data["pyscript_ready"] = _pyscript_ready` SHALL be present
- **AND** `app.run()` SHALL follow

#### Scenario: Inspecting generated HTML with profiling disabled
- **WHEN** `AppConfig.profile=False` (default) and a generated `index.html` is examined
- **THEN** the `<script type="py">` tag SHALL contain only the standard bootstrap (`from <app>.bootstrap import app; app.run()`)
- **AND** no profiling code SHALL appear

#### Scenario: Inspecting generated HTML with runtime_serving="local"
- **WHEN** `AppConfig(runtime_serving="local")` and a generated `index.html` is examined
- **THEN** `py-config` SHALL include `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"`
- **AND** `py-config` SHALL include `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"`
- **AND** the script tag SHALL reference `/_webcompy-assets/core.js`
- **AND** the CSS link SHALL reference `/_webcompy-assets/core.css`

#### Scenario: Inspecting generated HTML with runtime_serving="cdn" and wasm_serving="local"
- **WHEN** `AppConfig(runtime_serving="cdn", wasm_serving="local")`
- **THEN** `py-config` SHALL NOT include `interpreter`
- **AND** `py-config` SHALL include `lockFileURL` pointing to the CDN `pyodide-lock.json` URL
- **AND** the script tag and CSS link SHALL reference CDN URLs

#### Scenario: Inspecting generated HTML with runtime_serving="cdn" and wasm_serving="cdn"
- **WHEN** `AppConfig(runtime_serving="cdn", wasm_serving="cdn")` (defaults)
- **THEN** `py-config` SHALL NOT include `interpreter`
- **AND** `py-config` SHALL NOT include `lockFileURL`

### Requirement: CLI flags shall override config file values
CLI flags (`--dev`, `--port`, `--dist`) SHALL override values from `webcompy_server_config.py` and the defaults. When a flag is provided, it takes precedence; when not provided, the config file value or default is used.

#### Scenario: Overriding port with --port
- **WHEN** `webcompy_server_config.py` sets `server_config = ServerConfig(port=8080)`
- **AND** a developer runs `python -m webcompy start --port 3000`
- **THEN** the server SHALL start on port 3000

#### Scenario: Overriding dist with --dist
- **WHEN** `webcompy_server_config.py` sets `generate_config = GenerateConfig(dist="dist")`
- **AND** a developer runs `python -m webcompy generate --dist out`
- **THEN** static files SHALL be generated in the `out` directory

#### Scenario: Overriding dev mode with --dev
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** hot-reload SHALL be enabled regardless of `ServerConfig.dev` value

### Requirement: Application configuration shall support assets
`AppConfig` SHALL accept an `assets` parameter that maps string keys to file paths relative to the app package directory. These assets SHALL be included in the bundled wheel and accessible at runtime via `load_asset`.

#### Scenario: Configuring assets for application resources
- **WHEN** a developer specifies `assets={"logo": "images/logo.png", "config": "data/settings.json"}`
- **THEN** the CLI SHALL include the referenced files in the bundled wheel inside the app package tree
- **AND** an `_assets_registry.py` module SHALL be generated mapping `"logo"` to `"app/images/logo.png"` and `"config"` to `"app/data/settings.json"`
- **AND** those files SHALL be accessible via `load_asset("logo")` and `load_asset("config")` in the browser environment

#### Scenario: Omitting assets
- **WHEN** a developer does not specify `assets`
- **THEN** only Python source files, stub files, and `py.typed` markers SHALL be included in the wheel
- **AND** no `_assets_registry.py` module SHALL be generated

### Requirement: Assets shall be loadable by key at runtime
The `webcompy.assets` module SHALL provide a `load_asset(key: str) -> bytes` function and an `AssetNotFoundError` exception. When called, `load_asset` SHALL look up the key in the app's `_assets_registry` module and return the file content as `bytes` using `importlib.resources`.

#### Scenario: Loading an asset by key
- **WHEN** `load_asset("logo")` is called in browser code where `_assets_registry` maps `"logo"` to `"app/images/logo.png"`
- **THEN** the function SHALL return the raw `bytes` content of `app/images/logo.png`

#### Scenario: Asset key not found
- **WHEN** `load_asset("nonexistent")` is called
- **THEN** `AssetNotFoundError` SHALL be raised with the key as an attribute

#### Scenario: No assets registry module
- **WHEN** `load_asset` is called but the `app._assets_registry` module cannot be imported
- **THEN** `AssetNotFoundError` SHALL be raised

### Requirement: Dependency classification behavior SHALL depend on serve_all_deps
The behavior of pure-Python packages available in the Pyodide CDN SHALL depend on `AppConfig.serve_all_deps`. When `serve_all_deps=True`, CDN-available pure-Python packages SHALL be downloaded and bundled into the app wheel (replacing the prior behavior where they were neither bundled nor referenced in `py-config.packages`). When `serve_all_deps=False`, CDN-available pure-Python packages SHALL be loaded from the CDN by name via `py-config.packages`.

Dependencies listed in `AppConfig.dependencies` SHALL be classified using Pyodide lock data and local package inspection. WASM packages available in the Pyodide CDN SHALL be loaded from the CDN by name via `py-config.packages`. Pure-Python packages not in the Pyodide CDN SHALL be bundled into the app wheel. C-extension packages not in the Pyodide CDN SHALL cause an error.

When `AppConfig.dependencies` is `None`, the CLI SHALL auto-populate it from `pyproject.toml` before lock file generation. The resolution uses `AppConfig.dependencies_from` to determine which section of `pyproject.toml` to read. Version specifiers in `pyproject.toml` entries (e.g., `"flask>=3.0"`, `"numpy==2.2.5"`) SHALL be stripped before classification — only package names are used in `AppConfig.dependencies`; version pinning is handled by the lock file.

#### Scenario: serve_all_deps=True (default)
- **WHEN** `serve_all_deps=True` and a pure-Python package is in the Pyodide CDN
- **THEN** it SHALL be downloaded and bundled into the app wheel
- **AND** it SHALL NOT appear in `py-config.packages`

#### Scenario: serve_all_deps=False
- **WHEN** `serve_all_deps=False` and a pure-Python package is in the Pyodide CDN
- **THEN** it SHALL be loaded from the CDN by name via `py-config.packages`
- **AND** it SHALL NOT be bundled into the app wheel

#### Scenario: Pure-Python package not in Pyodide CDN (regardless of serve_all_deps)
- **WHEN** a pure-Python dependency is not in the Pyodide CDN
- **THEN** it SHALL be bundled from local installation into the app wheel
- **AND** it SHALL NOT appear in `py-config.packages`

#### Scenario: WASM package (regardless of serve_all_deps)
- **WHEN** a dependency is a WASM package in the Pyodide CDN
- **THEN** it SHALL be loaded from the CDN by name via `py-config.packages`
- **AND** it SHALL NOT be bundled

#### Scenario: C extension not available in Pyodide
- **WHEN** `AppConfig.dependencies=["some_c_ext"]` and `some_c_ext` is not in the Pyodide CDN and contains native extension files
- **THEN** an error SHALL be reported indicating the package is a C extension not available in Pyodide

#### Scenario: Auto-populated dependencies from pyproject.toml
- **WHEN** `AppConfig(dependencies=None, dependencies_from="browser")` and `pyproject.toml` has `[project.optional-dependencies] browser = ["numpy", "matplotlib"]`
- **THEN** dependencies SHALL be resolved to `["numpy", "matplotlib"]` before lock file generation
- **AND** the lock file SHALL be generated as if `dependencies=["numpy", "matplotlib"]` were explicitly set

#### Scenario: Version specifiers are stripped
- **WHEN** `pyproject.toml` has `dependencies = ["flask>=3.0", "click==8.1.7"]`
- **THEN** `AppConfig.dependencies` SHALL be set to `["flask", "click"]` (no version specifiers)

#### Scenario: Explicit dependencies bypass auto-population
- **WHEN** `AppConfig(dependencies=["numpy"])` (explicit list, not None)
- **THEN** no `pyproject.toml` reading SHALL occur
- **AND** `["numpy"]` SHALL be used as-is

### Requirement: The CLI shall download pure-Python packages from Pyodide CDN when serve_all_deps is True
When `serve_all_deps=True`, the CLI SHALL download pure-Python package wheels from the Pyodide CDN, verify their SHA256 hashes against the lock file, cache them locally, extract them, and bundle them into the app wheel.

#### Scenario: Downloading and bundling CDN packages
- **WHEN** a developer runs `python -m webcompy start --dev` with `serve_all_deps=True`
- **AND** the lock file contains pure-Python packages with `in_pyodide_cdn=True`
- **THEN** those packages SHALL be downloaded from the Pyodide CDN
- **AND** their SHA256 hashes SHALL be verified against the lock file
- **AND** the wheels SHALL be extracted and bundled into the app wheel
- **AND** downloaded wheels SHALL be cached at `~/.cache/webcompy/pyodide-packages/{pyodide_version}/`

#### Scenario: Cache hit
- **WHEN** a previously downloaded wheel exists in the cache with a matching SHA256 hash
- **THEN** the download SHALL be skipped
- **AND** the cached wheel SHALL be used

#### Scenario: SHA256 verification failure
- **WHEN** a downloaded wheel's SHA256 hash does not match the expected hash from the lock file
- **THEN** the build SHALL fail with a descriptive error
- **AND** the invalid cached file SHALL NOT be used

#### Scenario: Network failure with no cache
- **WHEN** the Pyodide CDN is unreachable and no cached wheel exists
- **THEN** the build SHALL fail with a descriptive error indicating network failure

#### Scenario: Generating static site with serve_all_deps=True
- **WHEN** a developer runs `python -m webcompy generate` with `serve_all_deps=True`
- **THEN** CDN packages SHALL be downloaded, verified, extracted, and bundled into the app wheel in `dist/_webcompy-app-package/`

### Requirement: The CLI shall pass CDN pure-Python package names to HTML when serve_all_deps is False
When `serve_all_deps=False`, pure-Python packages available in the Pyodide CDN SHALL be loaded from the CDN by name. Their package names SHALL appear in `py-config.packages` alongside WASM package names.

#### Scenario: Starting dev server with serve_all_deps=False
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **AND** the lock file contains pure-Python packages with `in_pyodide_cdn=True`
- **THEN** those package names SHALL appear in `py-config.packages`
- **AND** those packages SHALL NOT be bundled into the app wheel

#### Scenario: Generating static site with serve_all_deps=False
- **WHEN** a developer runs `python -m webcompy generate --no-serve-all-deps`
- **THEN** CDN pure-Python package names SHALL appear in the generated HTML `py-config.packages`
- **AND** the app wheel SHALL NOT contain those packages

### Requirement: The `webcompy lock` command shall generate or update the lock file
Running `webcompy lock` SHALL generate or update `webcompy-lock.json` in the app package directory. The lock file records Pyodide CDN package versions, bundled package versions and sources, and the Pyodide/PyScript versions used for classification.

#### Scenario: Generating a lock file
- **WHEN** a developer runs `webcompy lock` in a project with `AppConfig.dependencies=["flask", "numpy"]`
- **THEN** `webcompy-lock.json` SHALL be created in the app package directory

#### Scenario: Lock file already exists and dependencies unchanged
- **WHEN** `webcompy-lock.json` exists and `AppConfig.dependencies` matches
- **THEN** the existing lock file SHALL be validated and reused without network requests

#### Scenario: Lock file is stale
- **WHEN** `webcompy-lock.json` exists but `AppConfig.dependencies` has changed
- **THEN** the lock file SHALL be regenerated

### Requirement: The lock file shall be auto-generated on start and generate
The `webcompy start` and `webcompy generate` commands SHALL auto-generate `webcompy-lock.json` if it does not exist or is stale.

#### Scenario: Starting dev server without lock file
- **WHEN** a developer runs `python -m webcompy start --dev` without a `webcompy-lock.json`
- **THEN** the lock file SHALL be automatically generated before building wheels

#### Scenario: Generating static site with stale lock file
- **WHEN** a developer runs `python -m webcompy generate` and the lock file is stale
- **THEN** the lock file SHALL be regenerated before building wheels

### Requirement: The `webcompy lock` command shall support dependency export, sync, and install operations
The `webcompy lock` command SHALL support three additional operations beyond default lock file generation: `--export`, `--sync`, and `--install`. These operations enable synchronization between the WebComPy lock file and external Python package management tools. All three operations use auto-discovery to locate `requirements.txt` and `pyproject.toml` at the project root.

#### Scenario: Running `webcompy lock --export`
- **WHEN** a developer runs `webcompy lock --export`
- **THEN** a `requirements.txt` file SHALL be generated at the auto-discovered project root containing pinned versions for all locally-required packages from the lock file
- **AND** the lock file SHALL NOT be regenerated

#### Scenario: Running `webcompy lock --sync`
- **WHEN** a developer runs `webcompy lock --sync`
- **THEN** the command SHALL auto-discover `requirements.txt` and `pyproject.toml` at the project root
- **AND** compare the pinned versions against the lock file
- **AND** report matching versions, mismatches, and extra entries
- **AND** SHALL NOT modify the lock file

#### Scenario: Running `webcompy lock --install`
- **WHEN** a developer runs `webcompy lock --install`
- **THEN** a `requirements.txt` file SHALL be generated from the lock file via auto-discovery
- **AND** `uv pip install -r {path}` SHALL be executed if `uv` is available, otherwise `sys.executable -m pip install -r {path}`
- **AND** the exit code of the install command SHALL be the exit code of the `webcompy lock --install` command

#### Scenario: Combining mutually exclusive flags
- **WHEN** a developer runs `webcompy lock` with both `--export` and `--install`
- **THEN** an error SHALL be reported indicating that the operations are mutually exclusive

#### Scenario: Running `webcompy lock --export` without a lock file
- **WHEN** a developer runs `webcompy lock --export` without an existing `webcompy-lock.json`
- **THEN** an error SHALL be reported indicating that the lock file must be generated first by running `webcompy lock`

#### Scenario: Running `webcompy lock --sync` with sync_group configuration
- **WHEN** a developer has `LockfileSyncConfig(sync_group="browser")` in `webcompy_server_config.py`
- **AND** runs `webcompy lock --sync`
- **THEN** the command SHALL compare `[project.optional-dependencies.browser]` from `pyproject.toml` against the lock file

#### Scenario: Default `webcompy lock` unchanged
- **WHEN** a developer runs `webcompy lock` without any flags
- **THEN** the lock file SHALL be generated or updated (existing behavior preserved)

#### Scenario: Auto-populating dependencies from pyproject.toml
- **WHEN** a developer runs `webcompy lock` (or `webcompy start`, `webcompy generate`)
- **AND** `AppConfig.dependencies` is `None`
- **AND** `AppConfig.dependencies_from` is `"browser"`
- **THEN** the CLI SHALL read `[project.optional-dependencies.browser]` from `pyproject.toml`
- **AND** populate `app.config.dependencies` with the package names (stripping version specifiers)
- **AND** proceed with lock file generation using the populated dependencies

#### Scenario: Auto-populating dependencies when pyproject.toml is absent
- **WHEN** a developer runs `webcompy lock` with `AppConfig(dependencies=None)`
- **AND** no `pyproject.toml` is found above `app_package_path`
- **THEN** an error SHALL be reported instructing the developer to set `AppConfig.dependencies` explicitly

### Requirement: The CLI shall download and serve PyScript/Pyodide runtime assets locally when runtime_serving is local
When `runtime_serving="local"`, the CLI SHALL download PyScript core assets (`core.js`, `core.css`) and Pyodide runtime assets (`pyodide.mjs`, `pyodide.asm.wasm`, `pyodide.asm.js`, `python_stdlib.zip`, `pyodide-lock.json`) at build time and serve them from the same origin. PyScript core assets SHALL be placed at `/_webcompy-assets/` directly. Pyodide runtime assets SHALL be placed at `/_webcompy-assets/pyodide/`.

#### Scenario: Generating a static site with local runtime serving
- **WHEN** a developer runs `python -m webcompy generate` with `AppConfig(runtime_serving="local")`
- **THEN** PyScript core assets SHALL be downloaded to `dist/_webcompy-assets/`
- **AND** Pyodide runtime assets SHALL be downloaded to `dist/_webcompy-assets/pyodide/`
- **AND** the generated HTML SHALL reference local asset URLs instead of CDN URLs

#### Scenario: Starting the dev server with local runtime serving
- **WHEN** a developer runs `python -m webcompy start --dev` with `AppConfig(runtime_serving="local")`
- **THEN** the dev server SHALL serve PyScript core assets from `/_webcompy-assets/`
- **AND** the dev server SHALL serve Pyodide runtime assets from `/_webcompy-assets/pyodide/`
- **AND** the generated HTML SHALL reference local asset URLs

#### Scenario: Runtime assets are cached
- **WHEN** a developer runs `webcompy generate` or `webcompy start` with `runtime_serving="local"`
- **THEN** downloaded runtime assets SHALL be cached at `~/.cache/webcompy/runtime-assets/{pyscript_version}/`
- **AND** cached assets with matching versions SHALL be reused without network requests

### Requirement: Downloaded runtime assets SHALL be verified against lock file hashes
When `runtime_serving="local"`, the CLI SHALL compute SHA256 hashes of all downloaded runtime assets. If the lock file contains `runtime_assets` with SHA256 hashes (from a previous build), the CLI SHALL verify downloaded files against those hashes. On mismatch, the CLI SHALL raise an error. After verification, the CLI SHALL update the lock file with the computed hashes.

#### Scenario: First build with runtime_serving="local"
- **WHEN** a developer runs `webcompy generate --runtime-serving local` for the first time
- **THEN** runtime assets SHALL be downloaded and their SHA256 hashes computed
- **AND** the lock file SHALL be updated with `runtime_assets` entries containing URLs and computed SHA256 hashes
- **AND** no hash verification SHALL be performed (no prior hashes exist)

#### Scenario: Subsequent build with runtime_serving="local"
- **WHEN** a developer runs `webcompy generate --runtime-serving local` and the lock file contains `runtime_assets` with SHA256 hashes
- **THEN** downloaded runtime assets SHALL be verified against the lock file hashes
- **AND** on hash mismatch, the CLI SHALL raise an error
- **AND** the lock file SHALL be updated with the newly computed hashes

### Requirement: Temporary directories used for runtime asset downloads SHALL be cleaned up
When `webcompy generate` or `webcompy start` creates temporary directories for runtime asset downloads, those directories SHALL be cleaned up after use.

#### Scenario: Temporary directory cleanup after static site generation
- **WHEN** `webcompy generate --runtime-serving local` completes
- **THEN** any temporary directories created for runtime asset downloads SHALL be removed

#### Scenario: Temporary directory cleanup after dev server shutdown
- **WHEN** `webcompy start --dev --runtime-serving local` terminates
- **THEN** any temporary directories created for runtime asset downloads SHALL be removed

### Requirement: Runtime-local HTML shall reference local runtime asset URLs and configure PyScript for local Pyodide
In runtime-local mode, `generate_html()` SHALL replace PyScript and Pyodide CDN URLs with same-origin paths under `/_webcompy-assets/`. The PyScript `py-config` SHALL include `interpreter` and `lockFileURL` pointing to local Pyodide assets.

#### Scenario: Runtime-local PyScript script tag
- **WHEN** runtime-local mode is enabled
- **THEN** the `<script type="module" src="...">` tag SHALL reference `/_webcompy-assets/core.js`
- **AND** the CSS link SHALL reference `/_webcompy-assets/core.css`

#### Scenario: Runtime-local Pyodide interpreter configuration
- **WHEN** runtime-local mode is enabled
- **THEN** `py-config` SHALL include `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"`

#### Scenario: Runtime-local lock file URL
- **WHEN** runtime-local mode is enabled
- **THEN** `py-config` SHALL include `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"`

#### Scenario: Non-runtime-local HTML is unchanged
- **WHEN** `runtime_serving="cdn"` (default)
- **THEN** `py-config` SHALL NOT include `interpreter` or `lockFileURL`
- **AND** script and CSS tags SHALL reference CDN URLs

### Requirement: The CLI shall accept --runtime-serving value flag
The `start` and `generate` CLI subcommands SHALL accept `--runtime-serving <mode>` where `<mode>` is `"cdn"` or `"local"`. This overrides `AppConfig.runtime_serving`.

#### Scenario: Overriding with --runtime-serving local
- **WHEN** a developer runs `python -m webcompy start --dev --runtime-serving local`
- **THEN** `runtime_serving` SHALL be `"local"` for the session

#### Scenario: Overriding with --runtime-serving cdn
- **WHEN** a developer runs `python -m webcompy generate --runtime-serving cdn`
- **THEN** `runtime_serving` SHALL be `"cdn"` for the session

### Requirement: The CLI shall support standalone build mode as an orchestration of all local-serving modes
When `standalone=True` is set, the CLI SHALL enable all local-serving modes and orchestrate the download of all required assets from CDN. The resulting `py-config` SHALL include `interpreter` and `lockFileURL` pointing to local paths (because `standalone=True` defaults `runtime_serving="local"`).

#### Scenario: Generating a standalone static site
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** all PyScript and Pyodide runtime assets SHALL be downloaded to `dist/_webcompy-assets/`
- **AND** all WASM package wheels referenced in the lock file SHALL be downloaded to `dist/_webcompy-assets/packages/`
- **AND** pure-Python packages from the Pyodide CDN SHALL be bundled into the app wheel
- **AND** the generated HTML SHALL reference all local asset URLs
- **AND** `py-config` SHALL include `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"`
- **AND** `py-config` SHALL include `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"`

#### Scenario: Starting a standalone dev server
- **WHEN** a developer runs `python -m webcompy start --dev --standalone`
- **THEN** the dev server SHALL serve all assets from local paths
- **AND** the generated HTML SHALL reference local URLs for everything
- **AND** `py-config` SHALL include `interpreter` and `lockFileURL` pointing to local paths

#### Scenario: Overriding individual modes with --standalone
- **WHEN** a developer runs `python -m webcompy generate --standalone --wasm-serving cdn`
- **THEN** `wasm_serving` SHALL be `"cdn"` (CLI flag takes precedence)
- **AND** `runtime_serving` SHALL be `"local"` (standalone default)
- **AND** `serve_all_deps` SHALL be `True` (standalone forced)

### Requirement: The CLI shall support switching between standalone and non-standalone modes across invocations
Each CLI invocation creates a fresh `AppConfig` instance. The `--standalone` and `--no-standalone` CLI flags SHALL toggle all local-serving modes simultaneously in the new execution context. Switching from standalone to non-standalone mode across invocations SHALL revert the derived defaults to their non-standalone values. Explicitly set individual flags in the current invocation SHALL take precedence over standalone defaults.

#### Scenario: Switching from non-standalone to standalone across invocations
- **WHEN** a developer previously ran `python -m webcompy generate` (non-standalone) and then runs `python -m webcompy generate --standalone`
- **THEN** a fresh `AppConfig` SHALL be created with `standalone=True`
- **AND** the lock file SHALL be regenerated with `standalone: true`, `wasm_serving: "local"`, `runtime_serving: "local"`
- **AND** all runtime and WASM assets SHALL be downloaded and served locally

#### Scenario: Switching from standalone to non-standalone across invocations
- **WHEN** a developer previously ran `python -m webcompy generate --standalone` and then runs `python -m webcompy generate --no-standalone`
- **THEN** a fresh `AppConfig` SHALL be created with `standalone=False`
- **AND** the lock file SHALL be regenerated with `standalone: false`, `wasm_serving: "cdn"`, `runtime_serving: "cdn"`
- **AND** runtime and WASM assets SHALL NOT be downloaded
- **AND** `py-config` SHALL reference CDN URLs for the PyScript/Pyodide runtime

#### Scenario: Explicit overrides in the current invocation take precedence
- **WHEN** a developer runs `python -m webcompy generate --standalone --wasm-serving cdn`
- **THEN** `wasm_serving` SHALL be `"cdn"` (CLI flag takes precedence)
- **AND** `runtime_serving` SHALL be `"local"` (standalone default)