# CLI

## Purpose

The command-line interface bridges the gap between development and deployment. It provides three essential capabilities: a development server for live iteration, a static site generator for production deployment, and project scaffolding for starting new applications. These tools handle the complexity of packaging Python code for browser execution, serving it during development, and producing deployable output — tasks that are unique to a framework that runs Python in the browser.

## Requirements

### Requirement: The dev server shall serve the application with hot-reload
The development server SHALL be startable via `python -m webcompy start --dev` or `run_server(app)`. Both SHALL start a Starlette+uvicorn server that serves the application with SSE-based hot-reload. Dev mode is determined by `WebComPyServerConfig.dev` or the `--dev` CLI flag (which overrides the config file value). Server configuration SHALL be read from `WebComPyBuildConfig.server`.

#### Scenario: Starting dev server via CLI
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL start with hot-reload enabled
- **AND** `WebComPyServerConfig.dev` SHALL be overridden to `True`

#### Scenario: Starting dev server with custom port
- **WHEN** a developer runs `python -m webcompy start --port 3000`
- **THEN** the server SHALL start on port 3000
- **AND** the `--port` flag SHALL override `WebComPyServerConfig.port`

### Requirement: The generate command shall produce deployable static files
Static site generation SHALL be available via `python -m webcompy generate`. SSG settings SHALL be read from `WebComPyBuildConfig` (formerly `GenerateConfig`). The SSG process SHALL enter the app's DI scope for the entire generation pipeline.

#### Scenario: Generating via generate_static_site(app)
- **WHEN** a developer calls `generate_static_site(app)` with a `WebComPyApp` instance
- **THEN** a static site SHALL be generated in the `dist` directory

#### Scenario: Generating with custom dist via --dist flag
- **WHEN** a developer runs `python -m webcompy generate --dist out`
- **THEN** static files SHALL be generated in the `out` directory
- **AND** the `--dist` flag SHALL override `WebComPyBuildConfig.dist`

### Requirement: The init command shall scaffold a new project
Running `python -m webcompy init` SHALL create the necessary project structure including an `app.py` file (not `bootstrap.py`), a static directory, and a single `webcompy_config.py` configuration file containing `WebComPyBuildConfig`.

#### Scenario: Scaffolding a new project
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** template files SHALL be copied to the current directory
- **AND** a `static/` directory with `__init__.py` SHALL be created
- **AND** `webcompy_config.py` SHALL be created with `config = WebComPyBuildConfig(app, ...)`
- **AND** `app.py` SHALL be created (not `bootstrap.py`)

### Requirement: Application configuration shall be discovered via --config or webcompy_config.py
The CLI SHALL discover the app instance using `--config <import_path>` or by finding `webcompy_config.py` in the current working directory. The `--app` flag is removed. The config module SHALL contain a `config` attribute of type `WebComPyBuildConfig`. The CLI SHALL derive `app` (via `getattr(config.app_module, config.app_var)`), `app_package_path` (via `Path(config.app_module.__file__).parent`), and server settings (via `config.server`) from the `WebComPyBuildConfig` instance.

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

### Requirement: Generated HTML shall include PyScript bootstrapping
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

### Requirement: CLI flags shall override build config values
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

### Requirement: The dev server and SSG shall support both bundled and split wheel mode
The dev server SHALL build wheel(s) containing the webcompy framework (excluding `webcompy/cli/`), application code, and appropriate pure-Python dependencies based on `serve_all_deps`. When `wheel_mode="bundled"` (default), a single Python wheel is produced. When `wheel_mode="split"`, two wheel files are produced: a framework wheel (webcompy, excl. cli/) and an app wheel (app code + all dependencies bundled). All wheels SHALL be served from a `/_webcompy-app-package/` endpoint.

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

### Requirement: Dependency classification behavior SHALL depend on serve_all_deps
The behavior of pure-Python packages available in the Pyodide CDN SHALL depend on `WebComPyBuildConfig.serve_all_deps`. Dependencies listed in `WebComPyBuildConfig.dependencies` SHALL be classified using Pyodide lock data and local package inspection.

#### Scenario: serve_all_deps=True (default)
- **WHEN** `serve_all_deps=True` and a pure-Python package is in the Pyodide CDN
- **THEN** it SHALL be downloaded and bundled into the app wheel
- **AND** it SHALL NOT appear in `py-config.packages`

#### Scenario: serve_all_deps=False
- **WHEN** `serve_all_deps=False` and a pure-Python package is in the Pyodide CDN
- **THEN** it SHALL be loaded from the CDN by name via `py-config.packages`
- **AND** it SHALL NOT be bundled into the app wheel

### Requirement: The CLI shall download pure-Python packages from Pyodide CDN when serve_all_deps is True
When `serve_all_deps=True`, the CLI SHALL download pure-Python package wheels from the Pyodide CDN, verify their SHA256 hashes against the lock file, cache them locally, extract them, and bundle them into the app wheel.

#### Scenario: Downloading and bundling CDN packages
- **WHEN** a developer runs `python -m webcompy start --dev` with `serve_all_deps=True`
- **AND** the lock file contains pure-Python packages with `in_pyodide_cdn=True`
- **THEN** those packages SHALL be downloaded from the Pyodide CDN
- **AND** their SHA256 hashes SHALL be verified against the lock file
- **AND** the wheels SHALL be extracted and bundled into the app wheel

### Requirement: The CLI shall pass CDN pure-Python package names to HTML when serve_all_deps is False
When `serve_all_deps=False`, pure-Python packages available in the Pyodide CDN SHALL be loaded from the CDN by name. Their package names SHALL appear in `py-config.packages` alongside WASM package names.

### Requirement: The webcompy lock command shall generate or update the lock file
Running `webcompy lock` SHALL generate or update `webcompy-lock.json` in the app package directory. The lock file records Pyodide CDN package versions, bundled package versions and sources, and the Pyodide/PyScript versions used for classification.

### Requirement: The lock file shall be auto-generated on start and generate
The `webcompy start` and `webcompy generate` commands SHALL auto-generate `webcompy-lock.json` if it does not exist or is stale.

### Requirement: The webcompy lock command shall support dependency export, sync, and install operations
The `webcompy lock` command SHALL support `--export`, `--sync`, and `--install` operations. All three operations use `WebComPyBuildConfig.lockfile_sync_config` for configuration.

#### Scenario: Running webcompy lock --sync with sync_group configuration
- **WHEN** a developer has `LockfileSyncConfig(sync_group="browser")` in `webcompy_config.py`
- **AND** runs `webcompy lock --sync`
- **THEN** the command SHALL compare `[project.optional-dependencies.browser]` from `pyproject.toml` against the lock file

### Requirement: The dev server shall serve runtime assets locally
When `runtime_serving="local"`, the dev server SHALL serve all PyScript core bundle files and Pyodide runtime files from memory.

### Requirement: The dev server shall serve runtime and WASM assets from disk
When `runtime_serving="local"` or `wasm_serving="local"`, the dev server SHALL serve assets directly from the project-local cache directory using `FileResponse` or equivalent disk-based streaming.

### Requirement: Downloaded runtime assets SHALL be verified against lock file hashes
When `runtime_serving="local"`, the CLI SHALL compute SHA256 hashes of all downloaded runtime assets and verify them against the lock file.

### Requirement: Temporary directories used for runtime asset downloads SHALL be cleaned up
When `webcompy generate` or `webcompy start` creates temporary directories for CDN pure-Python wheel extraction for bundling, those directories SHALL be cleaned up after use.

### Requirement: Runtime-local HTML shall reference local runtime asset URLs and configure PyScript for local Pyodide
In runtime-local mode, `generate_html()` SHALL replace PyScript and Pyodide CDN URLs with same-origin paths under `/_webcompy-assets/`. The PyScript `py-config` SHALL include `interpreter` and `lockFileURL` pointing to local Pyodide assets.

### Requirement: CLI --wheel-mode flag shall override WebComPyBuildConfig.wheel_mode
The `start` and `generate` CLI subcommands SHALL accept `--wheel-mode <mode>` where `<mode>` is `"bundled"` or `"split"`. This SHALL override `WebComPyBuildConfig.wheel_mode`.

### Requirement: The CLI shall accept --runtime-serving value flag
The `start` and `generate` CLI subcommands SHALL accept `--runtime-serving <mode>` where `<mode>` is `"cdn"` or `"local"`. This overrides `WebComPyBuildConfig.runtime_serving`.

### Requirement: The CLI shall support standalone build mode as an orchestration of all local-serving modes
When `standalone=True` is set, the CLI SHALL enable all local-serving modes and orchestrate the download of all required assets from CDN.

#### Scenario: Generating a standalone static site
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** all PyScript and Pyodide runtime assets SHALL be downloaded to `dist/_webcompy-assets/`
- **AND** all WASM package wheels referenced in the lock file SHALL be downloaded to `dist/_webcompy-assets/packages/`
- **AND** pure-Python packages from the Pyodide CDN SHALL be bundled into the app wheel
- **AND** the generated HTML SHALL reference all local asset URLs

### Requirement: The CLI shall support switching between standalone and non-standalone modes across invocations
Each CLI invocation creates a fresh `WebComPyBuildConfig` instance. The `--standalone` and `--no-standalone` CLI flags SHALL toggle all local-serving modes simultaneously in the new execution context.

#### Scenario: Switching from non-standalone to standalone across invocations
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** a fresh `WebComPyBuildConfig` SHALL be created with `standalone=True`
- **AND** the lock file SHALL be regenerated with `standalone: true`, `wasm_serving: "local"`, `runtime_serving: "local"`

### Requirement: Application configuration shall support assets
`WebComPyBuildConfig` SHALL accept an `assets` parameter that maps string keys to file paths relative to the app package directory. These assets SHALL be included in the bundled wheel and accessible at runtime via `load_asset`.

### Requirement: Assets shall be loadable by key at runtime
The `webcompy.assets` module SHALL provide a `load_asset(key: str) -> bytes` function and an `AssetNotFoundError` exception.