# CLI — Delta: feat-pyscript-local-serving

## ADDED Requirements

### Requirement: The CLI shall support standalone build mode
When `standalone=True` is set in `GenerateConfig` or `ServerConfig`, or the `--standalone` CLI flag is provided, the CLI SHALL download all required PyScript and Pyodide runtime assets at build time and configure the application to serve them from the same origin instead of external CDN URLs.

#### Scenario: Generating a standalone static site
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** PyScript and Pyodide runtime assets SHALL be downloaded to `dist/_webcompy-assets/`
- **AND** the single bundled wheel SHALL be placed in `dist/_webcompy-app-package/`
- **AND** the generated HTML SHALL reference local asset URLs instead of CDN URLs

#### Scenario: Starting a standalone dev server
- **WHEN** a developer runs `python -m webcompy start --dev --standalone`
- **THEN** the dev server SHALL serve PyScript and Pyodide runtime assets from `/_webcompy-assets/`
- **AND** the generated HTML SHALL reference local asset URLs

### Requirement: Standalone HTML shall reference local runtime asset URLs
In standalone mode, `generate_html()` SHALL replace PyScript and Pyodide CDN URLs with same-origin paths under `/_webcompy-assets/`. The PyScript `py-config` SHALL include a `lockFileURL` pointing to the local `pyodide-lock.json`.

#### Scenario: Standalone PyScript configuration
- **WHEN** standalone mode is enabled
- **THEN** the `<script type="module" src="...">` tag SHALL reference `/_webcompy-assets/core.js`
- **AND** the CSS link SHALL reference `/_webcompy-assets/core.css`
- **AND** `py-config.packages` SHALL reference the single bundled wheel URL as usual

#### Scenario: Standalone Pyodide lock URL
- **WHEN** standalone mode is enabled
- **THEN** `py-config` SHALL include `lockFileURL` pointing to `/_webcompy-assets/pyodide-lock.json`

## MODIFIED Requirements

### Requirement: ServerConfig and GenerateConfig shall include a standalone flag
`ServerConfig` and `GenerateConfig` SHALL include a `standalone: bool = False` field.

#### Scenario: Enabling standalone mode in config
- **WHEN** a developer creates `GenerateConfig(standalone=True)`
- **THEN** the SSG SHALL produce a standalone build with all runtime assets served locally