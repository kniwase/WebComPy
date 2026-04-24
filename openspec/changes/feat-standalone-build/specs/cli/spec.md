# CLI — Delta: feat-standalone-build

## ADDED Requirements

### Requirement: The CLI shall support standalone build mode
When `standalone=True` is set in `GenerateConfig` or `ServerConfig`, or the `--standalone` CLI flag is provided, the CLI SHALL download all required PyScript and Pyodide assets at build time and configure the application to serve them from the same origin instead of external CDN URLs.

#### Scenario: Generating a standalone static site
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** all PyScript and Pyodide runtime assets SHALL be downloaded to `dist/_webcompy-assets/`
- **AND** all Pyodide package wheels referenced in the lock file SHALL be downloaded to `dist/_webcompy-assets/packages/`
- **AND** the generated HTML SHALL reference local asset URLs instead of CDN URLs

#### Scenario: Starting a standalone dev server
- **WHEN** a developer runs `python -m webcompy start --dev --standalone`
- **THEN** the dev server SHALL serve PyScript and Pyodide assets from `/_webcompy-assets/`
- **AND** the generated HTML SHALL reference local asset URLs

### Requirement: Standalone HTML shall reference local asset URLs
In standalone mode, `generate_html()` SHALL replace all CDN URLs with same-origin paths under `/_webcompy-assets/`. The PyScript `py-config` SHALL include a `lockFileURL` pointing to the local `pyodide-lock.json`.

#### Scenario: Standalone PyScript configuration
- **WHEN** standalone mode is enabled
- **THEN** the `<script type="module" src="...">` tag SHALL reference `/_webcompy-assets/core.js`
- **AND** the CSS link SHALL reference `/_webcompy-assets/core.css`
- **AND** `py-config.packages` SHALL reference local wheel URLs under `/_webcompy-assets/packages/`

#### Scenario: Standalone Pyodide lock URL
- **WHEN** standalone mode is enabled
- **THEN** `py-config` SHALL include `lockFileURL` pointing to `/_webcompy-assets/pyodide-lock.json`

## MODIFIED Requirements

### Requirement: ServerConfig and GenerateConfig shall include a standalone flag
`ServerConfig` and `GenerateConfig` SHALL include a `standalone: bool = False` field.

#### Scenario: Enabling standalone mode in config
- **WHEN** a developer creates `GenerateConfig(standalone=True)`
- **THEN** the SSG SHALL produce a standalone build with all assets served locally