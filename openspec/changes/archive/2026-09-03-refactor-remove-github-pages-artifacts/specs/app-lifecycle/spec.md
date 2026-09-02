# Spec delta: app-lifecycle

## MODIFIED Requirements

### Requirement: The SSG entry point shall be a module-level function
Static site generation SHALL use a module-level function (`generate_static_site`) that accepts an optional `WebComPyApp` instance, discovering it from the project configuration when omitted. The SSG process SHALL enter the app's DI scope for the entire generation pipeline (from dist configuration through HTML rendering) to ensure all `inject()` calls during route rendering and head management succeed.

#### Scenario: Generating a static site from a WebComPyApp
- **WHEN** a developer calls `generate_static_site(app)` on the server
- **THEN** a `dist/` directory SHALL be created with pre-rendered HTML for each route
- **AND** a bundled Python wheel SHALL be included
- **AND** static files SHALL be copied
- **AND** neither a `CNAME` file nor a `.nojekyll` file SHALL be created

#### Scenario: Generating with custom config
- **WHEN** a developer generates the static site with `WebComPyBuildConfig.dist` set to `"out"`
- **THEN** output SHALL be written to the `out` directory (resolved relative to the app package path)

#### Scenario: Generating via CLI with config files
- **WHEN** a developer runs `python -m webcompy generate`
- **THEN** the CLI SHALL discover the app instance via `webcompy_config.py` at the project root or `--app`
- **AND** `generate_config` SHALL be read from `webcompy_server_config.py` (searched in the app package first when `--app` is used, then at the project root)
