## MODIFIED Requirements

### Requirement: The dev server shall serve the application with hot-reload
The development server SHALL be startable via `python -m webcompy start --dev` or `run_server(app)`. Both SHALL start a Starlette+uvicorn server that serves the application with SSE-based hot-reload. Dev mode is determined by `ServerConfig.dev` or the `--dev` CLI flag (which overrides the config file value). The `--app` flag SHALL accept import paths using the `docs_app` module name instead of `docs_src`.

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

#### Scenario: Starting docs_app dev server
- **WHEN** a developer runs `python -m webcompy start --app docs_app.bootstrap:app`
- **THEN** the server SHALL start serving the docs_app application
- **AND** the app SHALL be discoverable via the `docs_app` module path