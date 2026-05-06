# CLI — Delta: feat-split-mode

## MODIFIED Requirements

### Requirement: The dev server and SSG shall support split wheel mode
When `wheel_mode="split"`, the dev server and SSG SHALL produce two wheel files: a framework wheel (webcompy, excl. cli/) and an app wheel (app code + all dependencies bundled). Both wheels SHALL be served from `/_webcompy-app-package/`. The generated HTML SHALL list both wheel URLs in `py-config.packages` alongside WASM package names.

#### Scenario: Starting the dev server in split mode
- **WHEN** a developer runs `python -m webcompy start --dev` with `AppConfig(wheel_mode="split")`
- **THEN** the server SHALL build two wheels: framework and app-with-deps
- **AND** the framework wheel SHALL receive `Cache-Control: max-age=86400, must-revalidate`
- **AND** the app wheel SHALL receive `Cache-Control: no-cache` in dev mode

#### Scenario: Generating a static site in split mode
- **WHEN** a developer runs `python -m webcompy generate` with `AppConfig(wheel_mode="split")`
- **THEN** two wheel files SHALL be placed in `dist/_webcompy-app-package/`
- **AND** the generated HTML SHALL reference both wheel URLs and WASM package names

### Requirement: CLI --wheel-mode flag shall override AppConfig.wheel_mode
The `start` and `generate` CLI subcommands SHALL accept `--wheel-mode <mode>` where `<mode>` is `"bundled"` or `"split"`. This SHALL override `AppConfig.wheel_mode`.

#### Scenario: Overriding with --wheel-mode split
- **WHEN** a developer runs `python -m webcompy start --dev --wheel-mode split`
- **THEN** split mode SHALL be used regardless of `AppConfig.wheel_mode`
