## ADDED Requirements

### Requirement: The dev server shall serve the docs_app application
The `--app` flag SHALL accept import paths using the `docs_app` module name. When the docs_app import path is provided, the server SHALL discover and serve the docs_app application.

#### Scenario: Starting docs_app dev server
- **WHEN** a developer runs `python -m webcompy start --app docs_app.bootstrap:app`
- **THEN** the server SHALL start serving the docs_app application
- **AND** the app SHALL be discoverable via the `docs_app` module path

### Requirement: The static site generator shall generate the docs_app site
The `--app` flag SHALL accept import paths using the `docs_app` module name for static site generation. When the docs_app import path is provided, the generator SHALL produce a static site from the docs_app application.

#### Scenario: Generating docs_app static site
- **WHEN** a developer runs `python -m webcompy generate --app docs_app.bootstrap:app`
- **THEN** the generator SHALL produce a static site from the docs_app application
- **AND** the output SHALL be written to the configured `dist` directory
