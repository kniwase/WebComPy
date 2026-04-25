# CLI — Delta: feat-wasm-local-serving

## ADDED Requirements

### Requirement: The CLI shall download and serve WASM packages locally when wasm_serving is local
When `wasm_serving="local"`, the CLI SHALL download WASM package wheels from the Pyodide CDN using URLs from `pyodide-lock.json` and serve them from the same origin.

#### Scenario: Generating a static site with local WASM serving
- **WHEN** a developer runs `python -m webcompy generate` with `AppConfig(wasm_serving="local")`
- **THEN** WASM package wheels SHALL be downloaded to `dist/_webcompy-assets/packages/`
- **AND** the generated HTML SHALL reference local wheel URLs in `py-config.packages`

#### Scenario: Starting the dev server with local WASM serving
- **WHEN** a developer runs `python -m webcompy start --dev` with `AppConfig(wasm_serving="local")`
- **THEN** the dev server SHALL serve WASM wheels from `/_webcompy-assets/packages/`
- **AND** the generated HTML SHALL reference local URLs