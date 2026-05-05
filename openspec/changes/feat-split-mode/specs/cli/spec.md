# CLI — Delta: feat-split-mode

## MODIFIED Requirements

### Requirement: The dev server and SSG shall support split wheel mode
When `wheel_mode="split"`, the dev server and SSG SHALL produce separate wheel files for the webcompy framework, each pure-Python dependency, and the app. All wheels SHALL be served from `/_webcompy-app-package/`. The generated HTML SHALL list all local wheel URLs in `py-config.packages` alongside WASM package names.

#### Scenario: Starting the dev server in split mode
- **WHEN** a developer runs `python -m webcompy start --dev` with `AppConfig(wheel_mode="split")`
- **THEN** the server SHALL build separate wheels for webcompy, each dependency, and the app
- **AND** each wheel SHALL be served at `/_webcompy-app-package/{filename}`
- **AND** framework and dependency wheels SHALL receive `Cache-Control: max-age=86400, must-revalidate`
- **AND** the app wheel SHALL receive `Cache-Control: no-cache` in dev mode

#### Scenario: Generating a static site in split mode
- **WHEN** a developer runs `python -m webcompy generate` with `AppConfig(wheel_mode="split")`
- **THEN** separate wheel files SHALL be placed in `dist/_webcompy-app-package/`
- **AND** the generated HTML SHALL reference all wheel URLs and WASM package names

### Requirement: CLI --wheel-mode flag shall override AppConfig.wheel_mode
The `start` and `generate` CLI subcommands SHALL accept `--wheel-mode <mode>` where `<mode>` is `"bundled"` or `"split"`. This SHALL override `AppConfig.wheel_mode`.

#### Scenario: Overriding with --wheel-mode split
- **WHEN** a developer runs `python -m webcompy start --dev --wheel-mode split`
- **THEN** split mode SHALL be used regardless of `AppConfig.wheel_mode`

#### Scenario: Default when no flag is provided
- **WHEN** a developer runs `python -m webcompy start --dev` without `--wheel-mode`
- **THEN** `wheel_mode` SHALL use the value from `AppConfig.wheel_mode` (default `"bundled"`)
