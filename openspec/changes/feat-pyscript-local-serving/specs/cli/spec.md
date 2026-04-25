# CLI — Delta: feat-pyscript-local-serving

## ADDED Requirements

### Requirement: The CLI shall support local-serving build mode
When `runtime_serving="local"` is set in `GenerateConfig` or `ServerConfig`, or the `--runtime-serving` CLI flag is provided, the CLI SHALL download all required PyScript and Pyodide runtime assets at build time and configure the application to serve them from the same origin instead of external CDN URLs.

#### Scenario: Generating a local-serving static site
- **WHEN** a developer runs `python -m webcompy generate --runtime-serving`
- **THEN** PyScript and Pyodide runtime assets SHALL be downloaded to `dist/_webcompy-assets/`
- **AND** the single bundled wheel SHALL be placed in `dist/_webcompy-app-package/`
- **AND** the generated HTML SHALL reference local asset URLs instead of CDN URLs

#### Scenario: Starting a local-serving dev server
- **WHEN** a developer runs `python -m webcompy start --dev --runtime-serving`
- **THEN** the dev server SHALL serve PyScript and Pyodide runtime assets from `/_webcompy-assets/`
- **AND** the generated HTML SHALL reference local asset URLs

### Requirement: Runtime-local HTML shall reference local runtime asset URLs
In runtime-local mode, `generate_html()` SHALL replace PyScript and Pyodide CDN URLs with same-origin paths under `/_webcompy-assets/`. The PyScript `py-config` SHALL include a `lockFileURL` pointing to the local `pyodide-lock.json`.

#### Scenario: Runtime-local PyScript configuration
- **WHEN** runtime-local mode is enabled
- **THEN** the `<script type="module" src="...">` tag SHALL reference `/_webcompy-assets/core.js`
- **AND** the CSS link SHALL reference `/_webcompy-assets/core.css`
- **AND** `py-config.packages` SHALL reference the single bundled wheel URL as usual

#### Scenario: Runtime-local Pyodide lock URL
- **WHEN** runtime-local mode is enabled
- **THEN** `py-config` SHALL include `lockFileURL` pointing to `/_webcompy-assets/pyodide-lock.json`

## MODIFIED Requirements

### Requirement: ServerConfig and GenerateConfig shall include a local-serving flag
`ServerConfig` and `GenerateConfig` SHALL include a `local-serving: bool = False` field.

#### Scenario: Enabling runtime-local mode in config
- **WHEN** a developer creates `GenerateConfig(runtime_serving="local")`
- **THEN** the SSG SHALL produce a local-serving build with all runtime assets served locally