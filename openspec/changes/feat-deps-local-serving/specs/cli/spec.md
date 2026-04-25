# CLI — Delta: feat-deps-local-serving

## ADDED Requirements

### Requirement: The CLI shall download pure-Python packages from Pyodide CDN when deps_serving is local-cdn
When `deps_serving="local-cdn"` is set, the CLI SHALL download pure-Python package wheels from the Pyodide CDN and extract them into the app wheel at build time.

#### Scenario: Starting the dev server with local-cdn
- **WHEN** a developer runs `python -m webcompy start --dev` with `AppConfig(deps_serving="local-cdn")`
- **THEN** pure-Python packages SHALL be downloaded from the Pyodide CDN and cached locally
- **AND** the packages SHALL be extracted into the app wheel

#### Scenario: Generating a static site with local-cdn
- **WHEN** a developer runs `python -m webcompy generate` with `AppConfig(deps_serving="local-cdn")`
- **THEN** pure-Python packages SHALL be downloaded and bundled into the static site output