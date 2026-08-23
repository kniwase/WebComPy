# CLI

## Purpose

The command-line interface bridges the gap between development and deployment. It provides three essential capabilities: a development server for live iteration, a static site generator for production deployment, and project scaffolding for starting new applications. These tools handle the complexity of packaging Python code for browser execution, serving it during development, and producing deployable output — tasks that are unique to a framework that runs Python in the browser.

In the refactored package structure, CLI functionality lives in the `webcompy_cli` package (formerly `webcompy.cli`). All imports from `webcompy.cli.*` are now `webcompy_cli.*`. Legacy import shims exist for backward compatibility.

## Requirements

### MODIFIED: The dev server shall serve the application with hot-reload
The development server SHALL be startable via `python -m webcompy start --dev` or `run_server(app)`. Both SHALL start a Starlette+uvicorn server that serves the application with SSE-based hot-reload. Dev mode is determined by `WebComPyServerConfig.dev` or the `--dev` CLI flag (which overrides the config file value). Server configuration SHALL be read from `WebComPyBuildConfig.server`. `WebComPyBuildConfig` and `WebComPyServerConfig` are imported from `webcompy_cli.config` (legacy shim `webcompy.cli.config` also works).

#### Scenario: Starting dev server via CLI
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL start with hot-reload enabled
- **AND** `WebComPyServerConfig.dev` SHALL be overridden to `True`

#### Scenario: Starting dev server with custom port
- **WHEN** a developer runs `python -m webcompy start --port 3000`
- **THEN** the server SHALL start on port 3000
- **AND** the `--port` flag SHALL override `WebComPyServerConfig.port`

### MODIFIED: The generate command shall produce deployable static files
Static site generation SHALL be available via `python -m webcompy generate`. SSG settings SHALL be read from `WebComPyBuildConfig` (formerly `GenerateConfig`), imported from `webcompy_cli.config` (legacy shim `webcompy.cli.config` also works). The SSG process SHALL enter the app's DI scope for the entire generation pipeline.

#### Scenario: Generating via generate_static_site(app)
- **WHEN** a developer calls `generate_static_site(app)` with a `WebComPyApp` instance
- **THEN** a static site SHALL be generated in the `dist` directory

#### Scenario: Generating with custom dist via --dist flag
- **WHEN** a developer runs `python -m webcompy generate --dist out`
- **THEN** static files SHALL be generated in the `out` directory
- **AND** the `--dist` flag SHALL override `WebComPyBuildConfig.dist`

### MODIFIED: The init command shall scaffold a new project
Running `python -m webcompy init` SHALL create the necessary project structure including an `app.py` file (not `bootstrap.py`), a static directory, and a single `webcompy_config.py` configuration file containing `WebComPyBuildConfig`. The generated `webcompy_config.py` template SHALL import `WebComPyBuildConfig` from `webcompy_cli.config`.

#### Scenario: Scaffolding a new project
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** template files SHALL be copied to the current directory
- **AND** a `static/` directory with `__init__.py` SHALL be created
- **AND** `webcompy_config.py` SHALL be created with `from webcompy_cli.config import WebComPyBuildConfig` and `config = WebComPyBuildConfig(app, ...)`
- **AND** `app.py` SHALL be created (not `bootstrap.py`)

### MODIFIED: Application configuration shall be discovered via --config or webcompy_config.py
The CLI SHALL discover the app instance using `--config <import_path>` or by finding `webcompy_config.py` in the current working directory. The `--app` flag is removed. The config module SHALL contain a `config` attribute of type `WebComPyBuildConfig`. The CLI SHALL derive `app` (via `getattr(config.app_module, config.app_var)`), `app_package_path` (via `Path(config.app_module.__file__).parent`), and server settings (via `config.server`) from the `WebComPyBuildConfig` instance. The generated `webcompy_config.py` template SHALL import `WebComPyBuildConfig` from `webcompy_cli.config`.

#### Scenario: Discovery via --config flag
- **WHEN** a developer runs `python -m webcompy start --config path.to.my_config`
- **THEN** the CLI SHALL import `path.to.my_config` and get the `config` attribute
- **AND** `config.app` SHALL be the computed `WebComPyApp` instance
- **AND** `config.app_package_path` SHALL be derived from `config.app_module.__file__`
- **AND** `config.server` SHALL provide server settings

#### Scenario: Discovery via root-level webcompy_config.py
- **WHEN** a developer runs `python -m webcompy start` without `--config`
- **AND** `webcompy_config.py` exists at the project root with `config = WebComPyBuildConfig(app, ...)`
- **THEN** the CLI SHALL import `webcompy_config` and get the `config` attribute

#### Scenario: No config file and no --config flag
- **WHEN** a developer runs `python -m webcompy start` without `--config`
- **AND** no `webcompy_config.py` exists at the project root
- **THEN** a clear error SHALL be raised: "Either --config flag or webcompy_config.py is required"

### MODIFIED: Generated HTML shall include PyScript bootstrapping
Every generated HTML page SHALL include PyScript bootstrapping. The bootstrap import SHALL use `from {package}.app import app` (not `from {package}.bootstrap import app`). The mount div SHALL use the ID from `WebComPyAppConfig.selector` (without the `#` prefix).

#### Scenario: Inspecting generated HTML
- **WHEN** a generated `index.html` is examined for an app package named `myapp`
- **THEN** it SHALL contain `<script type="py">` with `from myapp.app import app`
- **AND** the mount div SHALL use the selector ID from `WebComPyAppConfig.selector`

#### Scenario: Inspecting generated HTML with custom selector
- **WHEN** `WebComPyAppConfig(selector="#my-widget")` is used
- **THEN** the generated HTML SHALL contain `<div id="my-widget">`

#### Scenario: Inspecting generated HTML with profiling enabled
- **WHEN** `WebComPyAppConfig(profile=True)` and a generated `index.html` is examined
- **THEN** the `<script type="py">` tag SHALL start with `import time` and `_pyscript_ready = time.perf_counter()`
- **AND** after the app import, `app._profile_data["pyscript_ready"] = _pyscript_ready` SHALL be present
- **AND** `app.run()` SHALL follow

#### Scenario: Inspecting generated HTML with profiling disabled
- **WHEN** `WebComPyAppConfig(profile=False)` (default) and a generated `index.html` is examined
- **THEN** the `<script type="py">` tag SHALL contain only `from <package>.app import app; app.run()`

### MODIFIED: CLI flags shall override build config values
CLI flags SHALL override values from `WebComPyBuildConfig`. The following flags SHALL be supported: `--dev`, `--port`, `--dist`, `--config`, `--serve-all-deps`, `--no-serve-all-deps`, `--wasm-serving`, `--runtime-serving`, `--standalone`, `--no-standalone`, `--wheel-mode`.

#### Scenario: Overriding with --no-serve-all-deps
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **THEN** `WebComPyBuildConfig.serve_all_deps` SHALL be `False` for the session

#### Scenario: Overriding with --wasm-serving local
- **WHEN** a developer runs `python -m webcompy start --dev --wasm-serving local`
- **THEN** `WebComPyBuildConfig.wasm_serving` SHALL be `"local"` for the session

#### Scenario: Overriding with --runtime-serving local
- **WHEN** a developer runs `python -m webcompy start --dev --runtime-serving local`
- **THEN** `WebComPyBuildConfig.runtime_serving` SHALL be `"local"` for the session

#### Scenario: Overriding with --standalone
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** `WebComPyBuildConfig.standalone` SHALL be `True` for the session

### MODIFIED: The dev server and SSG shall support both bundled and split wheel mode
The dev server SHALL build wheel(s) containing the webcompy framework and application code. In the refactored package structure, the browser wheel contains only the `webcompy` core package (not `webcompy_cli`, `webcompy_server`, or `webcompy_testing`). The `_BROWSER_ONLY_EXCLUDE` mechanism is no longer needed because the packages are physically separate. When `wheel_mode="bundled"` (default), a single Python wheel is produced. When `wheel_mode="split"`, two wheel files are produced: a framework wheel (`webcompy` core only) and an app wheel (app code + all dependencies bundled). All wheels SHALL be served from a `/_webcompy-app-package/` endpoint.

#### Scenario: Starting the dev server with serve_all_deps=True
- **WHEN** a developer runs `python -m webcompy start --dev` with `serve_all_deps=True` (default)
- **THEN** the server SHALL build a single wheel containing webcompy (excl. cli), app code, and ALL pure-Python dependencies
- **AND** `py-config.packages` SHALL contain only the app wheel URL and WASM package names
- **AND** CDN-downloaded pure-Python packages SHALL be included in the wheel

#### Scenario: Starting the dev server with serve_all_deps=False
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **THEN** the server SHALL build a single wheel containing webcompy (excl. cli), app code, and locally-bundled dependencies only
- **AND** `py-config.packages` SHALL contain the app wheel URL, WASM package names, AND CDN pure-Python package names

#### Scenario: Starting the dev server in split mode
- **WHEN** a developer runs `python -m webcompy start --dev` with `WebComPyBuildConfig(app, wheel_mode="split")`
- **THEN** the server SHALL build two wheels: framework and app-with-deps
- **AND** the framework wheel SHALL receive `Cache-Control: max-age=86400, must-revalidate`
- **AND** the app wheel SHALL receive `Cache-Control: no-cache` in dev mode

#### Scenario: Generating a static site in split mode
- **WHEN** a developer runs `python -m webcompy generate` with `WebComPyBuildConfig(app, wheel_mode="split")`
- **THEN** two wheel files SHALL be placed in `dist/_webcompy-app-package/`
- **AND** the generated HTML SHALL reference both wheel URLs and WASM package names

### MODIFIED: Dependency classification behavior SHALL depend on serve_all_deps
The behavior of pure-Python packages available in the Pyodide CDN SHALL depend on `WebComPyBuildConfig.serve_all_deps`. Dependencies listed in `WebComPyBuildConfig.dependencies` SHALL be classified using Pyodide lock data and local package inspection.

#### Scenario: serve_all_deps=True (default)
- **WHEN** `serve_all_deps=True` and a pure-Python package is in the Pyodide CDN
- **THEN** it SHALL be downloaded and bundled into the app wheel
- **AND** it SHALL NOT appear in `py-config.packages`

#### Scenario: serve_all_deps=False
- **WHEN** `serve_all_deps=False` and a pure-Python package is in the Pyodide CDN
- **THEN** it SHALL be loaded from the CDN by name via `py-config.packages`
- **AND** it SHALL NOT be bundled into the app wheel

### MODIFIED: The CLI shall download pure-Python packages from Pyodide CDN when serve_all_deps is True
When `serve_all_deps=True`, the CLI SHALL download pure-Python package wheels from the Pyodide CDN, verify their SHA256 hashes against the lock file, cache them locally, extract them, and bundle them into the app wheel.

#### Scenario: Downloading and bundling CDN packages
- **WHEN** a developer runs `python -m webcompy start --dev` with `serve_all_deps=True`
- **AND** the lock file contains pure-Python packages with `in_pyodide_cdn=True`
- **THEN** those packages SHALL be downloaded from the Pyodide CDN
- **AND** their SHA256 hashes SHALL be verified against the lock file
- **AND** the wheels SHALL be extracted and bundled into the app wheel

### MODIFIED: The CLI shall pass CDN pure-Python package names to HTML when serve_all_deps is False
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

### MODIFIED: The webcompy lock command shall generate or update the lock file
Running `webcompy lock` SHALL generate or update `webcompy-lock.json` in the app package directory. The lock file records Pyodide CDN package versions, bundled package versions and sources, and the Pyodide/PyScript versions used for classification.

#### Scenario: Generating a lock file
- **WHEN** a developer runs `webcompy lock` with `WebComPyBuildConfig(app, dependencies=["flask", "numpy"])`
- **THEN** `webcompy-lock.json` SHALL be created in the app package directory

#### Scenario: Lock file already exists and dependencies unchanged
- **WHEN** `webcompy-lock.json` exists and `WebComPyBuildConfig.dependencies` matches
- **THEN** the existing lock file SHALL be validated and reused without network requests

#### Scenario: Lock file is stale
- **WHEN** `webcompy-lock.json` exists but `WebComPyBuildConfig.dependencies` has changed
- **THEN** the lock file SHALL be regenerated

### MODIFIED: The lock file shall be auto-generated on start and generate
The `webcompy start` and `webcompy generate` commands SHALL auto-generate `webcompy-lock.json` if it does not exist or is stale.

#### Scenario: Starting dev server without lock file
- **WHEN** a developer runs `python -m webcompy start --dev` without a `webcompy-lock.json`
- **THEN** the lock file SHALL be automatically generated before building wheels

#### Scenario: Generating static site with stale lock file
- **WHEN** a developer runs `python -m webcompy generate` and the lock file is stale
- **THEN** the lock file SHALL be regenerated before building wheels

### MODIFIED: The webcompy lock command shall support dependency export, sync, and install operations
The `webcompy lock` command SHALL support `--export`, `--sync`, and `--install` operations. All three operations use `WebComPyBuildConfig.lockfile_sync_config` for configuration. The command is invoked as `webcompy_cli lock` in the new package structure (legacy shim `webcompy lock` also works via `webcompy.__main__`).

#### Scenario: Running webcompy lock --export
- **WHEN** a developer runs `webcompy lock --export`
- **THEN** a `requirements.txt` file SHALL be generated containing pinned versions for all locally-required packages from the lock file

#### Scenario: Running webcompy lock --sync with sync_group configuration
- **WHEN** a developer has `LockfileSyncConfig(sync_group="browser")` in `webcompy_config.py`
- **AND** runs `webcompy lock --sync`
- **THEN** the command SHALL compare `[project.optional-dependencies.browser]` from `pyproject.toml` against the lock file

#### Scenario: Running webcompy lock --install
- **WHEN** a developer runs `webcompy lock --install`
- **THEN** `uv pip install -r {path}` SHALL be executed if `uv` is available, otherwise `sys.executable -m pip install -r {path}`

### MODIFIED: The dev server shall serve runtime assets locally
When `runtime_serving="local"`, the dev server SHALL serve all PyScript core bundle files and Pyodide runtime files from memory.

#### Scenario: Dev server with runtime_serving=local serves all PyScript bundle files
- **WHEN** a developer starts the dev server with `runtime_serving="local"`
- **THEN** all PyScript core bundle `.js` and `.css` files SHALL be available at `/_webcompy-assets/{filename}`

### MODIFIED: The dev server shall serve runtime and WASM assets from disk
When `runtime_serving="local"` or `wasm_serving="local"`, the dev server SHALL serve assets directly from the project-local cache directory using `FileResponse` or equivalent disk-based streaming.

#### Scenario: Serving a local runtime asset
- **WHEN** a browser requests `/_webcompy-assets/core.js` and `runtime_serving="local"`
- **THEN** the server SHALL stream the file from the project-local cache directory
- **AND** the file SHALL NOT be fully loaded into memory before the response begins

### MODIFIED: Downloaded runtime assets SHALL be verified against lock file hashes
When `runtime_serving="local"`, the CLI SHALL compute SHA256 hashes of all downloaded runtime assets and verify them against the lock file.

#### Scenario: First build with runtime_serving=local
- **WHEN** a developer runs `webcompy generate --runtime-serving local` for the first time
- **THEN** runtime assets SHALL be downloaded and their SHA256 hashes computed
- **AND** the lock file SHALL be updated with `runtime_assets` entries containing URLs and computed SHA256 hashes

#### Scenario: Subsequent build with runtime_serving=local
- **WHEN** a developer runs `webcompy generate --runtime-serving local` and the lock file contains `runtime_assets` with SHA256 hashes
- **THEN** downloaded runtime assets SHALL be verified against the lock file hashes

### Requirement: Generated HTML shall serialize the loading configuration onto the loading element

Every generated HTML page SHALL serialize the normalized `WebComPyAppConfig.loading` configuration so that browser-side loading behavior is derivable from the DOM alone: the `#webcompy-loading` element SHALL carry `data-wc-mode`, `data-wc-interaction` (content mode), and `data-wc-fade` attributes plus `--wc-delay`/`--wc-fade` style variables (reveal and fade timing), and the loading controller script SHALL embed the resolved timeout in its configuration. When dormant treatment applies, the generated `<body>` element SHALL carry the boot-state class defined by the `loading-screen` capability.

#### Scenario: Default serialization

- **WHEN** a page is generated with default loading configuration
- **THEN** the `#webcompy-loading` element SHALL carry `data-wc-*` attributes reflecting the defaults
- **AND** in `content` mode the `<body>` element SHALL carry the boot-state class

#### Scenario: Custom values serialized

- **WHEN** a page is generated with `loading={"fade_out_ms": 400, "interaction": "inert"}`
- **THEN** the `#webcompy-loading` element attributes SHALL reflect those values

#### Scenario: Custom template receives resolved mechanic attributes

- **WHEN** a custom template's `#webcompy-loading` element does not set mechanic attributes
- **THEN** generation SHALL inject the resolved `data-wc-mode`, `data-wc-interaction` (content mode), and `data-wc-fade` attributes, plus `--wc-delay`/`--wc-fade` style variables, onto the element
- **AND** attributes set by the template author SHALL be preserved unchanged

### Requirement: Generated HTML shall include the loading controller script

Every generated HTML page SHALL include an inline classic `<script>` (the loading controller) immediately after the `#webcompy-loading` element. The controller SHALL register `window` listeners for PyScript progress lifecycle events, drive stage labels, sub-status, progress bar, and the stall watchdog, and SHALL be dependency-free. Being a classic script placed before the deferred module script that loads PyScript, it SHALL be guaranteed to observe every boot progress event.

#### Scenario: Controller present in generated HTML

- **WHEN** a generated `index.html` is examined
- **THEN** an inline classic script implementing the loading controller SHALL appear immediately after the `#webcompy-loading` element
- **AND** the controller SHALL NOT be a module script

#### Scenario: Controller present for both dev server and SSG output

- **WHEN** HTML is produced by the dev server SSR handler or by `webcompy generate`
- **THEN** both outputs SHALL include the loading controller

### Requirement: Custom loading templates shall be validated at generation time

When the loading configuration provides a custom `template` (HTML string or file path), HTML generation SHALL validate that the markup contains exactly one element with `id="webcompy-loading"`. If the contract is violated, generation SHALL fail with a clear error. If the template contains none of the documented progress hooks (`data-wc-status`, `data-wc-substatus`, `data-wc-bar`, `data-wc-timeout`, `data-wc-reload`), generation SHALL succeed with a warning. A template given as a file path SHALL be resolved relative to the app package directory; a missing file SHALL fail generation with a clear error.

#### Scenario: Valid custom template

- **WHEN** a custom template contains `id="webcompy-loading"` and at least one documented hook
- **THEN** generation SHALL succeed and the generated page SHALL contain the custom markup

#### Scenario: Missing contract ID fails generation

- **WHEN** a custom template lacks `id="webcompy-loading"`
- **THEN** generation SHALL fail with an error naming the missing contract

#### Scenario: Missing template file fails generation

- **WHEN** `template` references a file path that does not exist relative to the app package
- **THEN** generation SHALL fail with an error naming the path

### MODIFIED: Temporary directories used for runtime asset downloads SHALL be cleaned up
When `webcompy generate` or `webcompy start` creates temporary directories for CDN pure-Python wheel extraction for bundling, those directories SHALL be cleaned up after use.

#### Scenario: Temporary directory cleanup after CDN wheel extraction
- **WHEN** `webcompy generate` or `webcompy start` with `serve_all_deps=True` completes
- **AND** CDN pure-Python wheels were extracted for bundling
- **THEN** any temporary directories created for wheel extraction SHALL be removed

### MODIFIED: Runtime-local HTML shall reference local runtime asset URLs and configure PyScript for local Pyodide
In runtime-local mode, `generate_html()` SHALL replace PyScript and Pyodide CDN URLs with same-origin paths under `/_webcompy-assets/`. The PyScript `py-config` SHALL include `interpreter` and `lockFileURL` pointing to local Pyodide assets.

#### Scenario: Runtime-local PyScript script tag
- **WHEN** runtime-local mode is enabled
- **THEN** the `<script type="module" src="...">` tag SHALL reference `/_webcompy-assets/core.js`
- **AND** the CSS link SHALL reference `/_webcompy-assets/core.css`

#### Scenario: Non-runtime-local HTML is unchanged
- **WHEN** `runtime_serving="cdn"` (default)
- **THEN** `py-config` SHALL NOT include `interpreter` or `lockFileURL`
- **AND** script and CSS tags SHALL reference CDN URLs

### MODIFIED: CLI --wheel-mode flag shall override WebComPyBuildConfig.wheel_mode
The `start` and `generate` CLI subcommands SHALL accept `--wheel-mode <mode>` where `<mode>` is `"bundled"` or `"split"`. This SHALL override `WebComPyBuildConfig.wheel_mode`.

#### Scenario: Overriding with --wheel-mode split
- **WHEN** a developer runs `python -m webcompy start --dev --wheel-mode split`
- **THEN** split mode SHALL be used regardless of `WebComPyBuildConfig.wheel_mode`

### MODIFIED: The CLI shall accept --runtime-serving value flag
The `start`, `generate`, and `inspect serve` CLI subcommands SHALL accept `--runtime-serving <mode>` where `<mode>` is `"cdn"` or `"local"`. This overrides `WebComPyBuildConfig.runtime_serving`.

#### Scenario: Overriding with --runtime-serving local
- **WHEN** a developer runs `python -m webcompy start --dev --runtime-serving local`
- **THEN** `runtime_serving` SHALL be `"local"` for the session

#### Scenario: Overriding with --runtime-serving local for inspect serve
- **WHEN** a developer runs `webcompy inspect serve --config my_app.config --runtime-serving local`
- **THEN** `runtime_serving` SHALL be `"local"` for the session

### MODIFIED: The CLI shall support standalone build mode as an orchestration of all local-serving modes
When `standalone=True` is set, the CLI SHALL enable all local-serving modes and orchestrate the download of all required assets from CDN.

#### Scenario: Generating a standalone static site
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** all PyScript and Pyodide runtime assets SHALL be downloaded to `dist/_webcompy-assets/`
- **AND** all WASM package wheels referenced in the lock file SHALL be downloaded to `dist/_webcompy-assets/packages/`
- **AND** pure-Python packages from the Pyodide CDN SHALL be bundled into the app wheel
- **AND** the generated HTML SHALL reference all local asset URLs

### MODIFIED: The CLI shall support switching between standalone and non-standalone modes across invocations
Each CLI invocation creates a fresh `WebComPyBuildConfig` instance. The `--standalone` and `--no-standalone` CLI flags SHALL toggle all local-serving modes simultaneously in the new execution context.

#### Scenario: Switching from non-standalone to standalone across invocations
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** a fresh `WebComPyBuildConfig` SHALL be created with `standalone=True`
- **AND** the lock file SHALL be regenerated with `standalone: true`, `wasm_serving: "local"`, `runtime_serving: "local"`

### MODIFIED: The dev server and SSG shall serve application resource files

The dev/prod SSR server SHALL expose a `GET {base_url}_webcompy-resource/{path:path}` endpoint that serves allow-listed application resource files. The endpoint SHALL be registered in both dev and prod modes. `WebComPyBuildConfig` SHALL accept `resources: list[str] | None` and `resource_exclude: list[str] | None` fields for configuring which files are served via the resource endpoint. The `assets: dict[str, str] | None` field is REMOVED (superseded by the resource auto-detection mechanism). Resource paths SHALL be package-relative (POSIX-style, no `..` segments).

#### Scenario: Allow-listed resource is served
- **WHEN** the allow-list contains `"templates/card.html"` and the file exists
- **AND** a GET request arrives for `{base_url}_webcompy-resource/templates/card.html`
- **THEN** the response SHALL be HTTP 200 with the file's UTF-8 text body and `Content-Type: text/html`

#### Scenario: Non-allow-listed resource returns 404
- **WHEN** the allow-list does NOT contain `"secrets/credentials.json"`
- **AND** a GET request arrives for `{base_url}_webcompy-resource/secrets/credentials.json`
- **THEN** the response SHALL be HTTP 404
- **AND** no filesystem access SHALL occur

#### Scenario: Path traversal rejected
- **WHEN** a GET request arrives for `{base_url}_webcompy-resource/../webcompy_config.py`
- **THEN** the response SHALL be HTTP 404 (resolved outside allow-list) or 403 (realpath outside root)
- **AND** the file SHALL NOT be returned

#### Scenario: Cache-Control in dev mode
- **WHEN** the server runs in dev mode
- **THEN** resource responses SHALL include `Cache-Control: no-cache`

#### Scenario: Cache-Control in prod mode
- **WHEN** the server runs in prod mode
- **THEN** resource responses SHALL include `Cache-Control: public, max-age=3600`

### MODIFIED: Static site generation shall copy allow-listed resources to dist

`generate_static_site` SHALL copy every allow-listed resource to `{dist_dir}/_webcompy-resource/{path}` preserving the package-relative path's directory structure. The copy SHALL happen after the dist directory is created and before static-file and app-package copies.

#### Scenario: Allow-listed resources appear in dist
- **WHEN** the allow-list contains `"templates/card.html"`, `"assets/icons/star.svg"`, and `"styles/main.css"`
- **AND** `generate_static_site(app)` runs
- **THEN** `{dist_dir}/_webcompy-resource/templates/card.html` SHALL exist
- **AND** `{dist_dir}/_webcompy-resource/assets/icons/star.svg` SHALL exist
- **AND** `{dist_dir}/_webcompy-resource/styles/main.css` SHALL exist
- **AND** each file's contents SHALL match the source

#### Scenario: Non-allow-listed files are not copied
- **WHEN** the app package contains `secrets/credentials.json` and `webcompy_config.py`
- **AND** these paths are NOT in the allow-list
- **THEN** `{dist_dir}/_webcompy-resource/secrets/credentials.json` SHALL NOT exist
- **AND** `{dist_dir}/_webcompy-resource/webcompy_config.py` SHALL NOT exist

#### Scenario: Static host serves the same URL
- **WHEN** the generated `dist/` directory is deployed to a static host
- **AND** a browser fetches `{base_url}_webcompy-resource/templates/card.html`
- **THEN** the host SHALL serve the copied file with the same content as the live SSR endpoint would have

### ADDED: The server shall mount user-provided ASGI applications
The dev/prod server SHALL support mounting user-provided ASGI applications at configured path prefixes. Mounts SHALL be declared via `WebComPyServerConfig.mounts`, a zero-argument callable returning `dict[str, ASGIApp]` (path prefix → ASGI app) or `None`. `create_asgi_app()` SHALL invoke the callable at most once per serving app construction and SHALL insert one Starlette `Mount` per entry into the route list immediately before the SSR catch-all route (`/{path:path}`), after all framework-internal and static-file routes. Mount path prefixes SHALL NOT be prefixed by `app.base_url`.

#### Scenario: Mounting a FastAPI app at /api
- **WHEN** `WebComPyServerConfig(mounts=lambda: {"/api": fastapi_app})` is configured and the server is running
- **THEN** a request to `/api/users` SHALL be handled by `fastapi_app`
- **AND** a request to a page route SHALL still be handled by SSR

#### Scenario: Mount reachable under non-root base_url
- **WHEN** `base_url="/myapp/"` is configured and `/api` is a configured mount
- **THEN** a request to `/api/users` SHALL reach the mounted app (mount paths are NOT prefixed by `base_url`)

#### Scenario: Mounts take precedence over the catch-all
- **WHEN** a mount is configured at `/api` and no page route matches `/api/anything`
- **THEN** requests to `/api/...` SHALL be routed to the mounted app, not to SSR
- **AND** unmatched paths inside the mount SHALL produce the mounted app's own 404

#### Scenario: No mounts configured preserves current behavior
- **WHEN** `mounts` is `None` (default)
- **THEN** the route table SHALL be exactly as before this change

### ADDED: Mount path collisions shall fail fast at startup
`create_asgi_app()` SHALL validate mount prefixes before constructing the ASGI app. A mount prefix that starts with `/_webcompy` (framework-reserved) SHALL be rejected. A mount prefix that normalizes to `/` (root mounting) SHALL be rejected, as it would shadow the SSR catch-all and all page routes. A mount prefix that collides with a registered page route SHALL be rejected. On any collision, the server SHALL raise an error listing all conflicting paths before serving begins; the same validation SHALL apply during SSG.

#### Scenario: Reserved prefix collision
- **WHEN** a mount is declared at `/_webcompy-api`
- **THEN** startup SHALL fail with an error naming `/_webcompy-api` as reserved

#### Scenario: Page route collision
- **WHEN** a page route `/admin` exists and a mount is declared at `/admin`
- **THEN** startup SHALL fail with an error listing the conflict

#### Scenario: Root mount rejected
- **WHEN** a mount is declared at `/` (or an empty prefix)
- **THEN** startup SHALL fail with an error naming the prefix

### Requirement: The server shall expose a JSON-RPC dispatcher endpoint at a reserved prefix

When one or more RPC contracts are bound, the dev/prod server SHALL expose the JSON-RPC dispatcher endpoint at `/_webcompy-rpc` (a framework-reserved prefix under `/_webcompy`). The dispatcher SHALL be inserted as a framework-internal route via the same route-insertion point as user-provided ASGI mounts, and SHALL NOT be subject to the user-mount collision validation (which rejects `/_webcompy*` prefixes). The dispatcher MAY be registered at a custom path. When no contracts are bound, the endpoint SHALL NOT be added to the route table.

#### Scenario: Endpoint present when procedures are registered
- **WHEN** at least one contract is bound and the server is running
- **THEN** POST requests to `/_webcompy-rpc` SHALL be handled by the dispatcher

#### Scenario: Endpoint absent when no procedures are registered
- **WHEN** no contracts are bound
- **THEN** the route table SHALL NOT contain `/_webcompy-rpc`

#### Scenario: Custom dispatcher path
- **WHEN** the dispatcher is registered at a user-chosen path
- **THEN** POST requests to that path SHALL be handled by the dispatcher
