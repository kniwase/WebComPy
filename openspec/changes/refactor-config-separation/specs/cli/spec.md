## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Application configuration shall be discovered via two-file pattern
**Reason**: Consolidated into single `webcompy_config.py` with `WebComPyBuildConfig`.
**Migration**: Merge `webcompy_server_config.py` into `webcompy_config.py`. Use `config = WebComPyBuildConfig(app, ...)` with `server=WebComPyServerConfig(...)` for server settings.