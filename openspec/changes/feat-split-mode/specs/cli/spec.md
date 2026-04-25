# CLI — Delta: feat-split-mode

## MODIFIED Requirements

### Requirement: The dev server and SSG shall support split wheel mode
When `wheel_mode="split"`, the dev server and SSG SHALL produce separate wheel files for the webcompy framework, each pure-Python dependency, and the app. The generated HTML SHALL configure PyScript to load the wheels via the validated loading strategy (TBD based on experiments).

#### Scenario: Starting the dev server in split mode
- **WHEN** a developer runs `python -m webcompy start --dev` with `AppConfig(wheel_mode="split")`
- **THEN** the server SHALL build separate wheels for webcompy, each dependency, and the app
- **AND** each wheel SHALL be served at a stable URL with appropriate cache headers

#### Scenario: Generating a static site in split mode
- **WHEN** a developer runs `python -m webcompy generate` with `AppConfig(wheel_mode="split")`
- **THEN** separate wheel files SHALL be placed in `dist/_webcompy-app-package/`
- **AND** the generated HTML SHALL reference all wheel URLs