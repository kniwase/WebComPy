# CLI — Delta: feat-standalone

## ADDED Requirements

### Requirement: The CLI shall support standalone build mode as an orchestration of all local-serving modes
When `standalone=True` is set, the CLI SHALL enable all local-serving modes and orchestrate the download of all required assets from CDN. The resulting `py-config` SHALL include `interpreter` and `lockFileURL` pointing to local paths (because `standalone=True` defaults `runtime_serving="local"`).

#### Scenario: Generating a standalone static site
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** all PyScript and Pyodide runtime assets SHALL be downloaded to `dist/_webcompy-assets/`
- **AND** all WASM package wheels referenced in the lock file SHALL be downloaded to `dist/_webcompy-assets/packages/`
- **AND** pure-Python packages from the Pyodide CDN SHALL be bundled into the app wheel
- **AND** the generated HTML SHALL reference all local asset URLs
- **AND** `py-config` SHALL include `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"`
- **AND** `py-config` SHALL include `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"`

#### Scenario: Starting a standalone dev server
- **WHEN** a developer runs `python -m webcompy start --dev --standalone`
- **THEN** the dev server SHALL serve all assets from local paths
- **AND** the generated HTML SHALL reference local URLs for everything
- **AND** `py-config` SHALL include `interpreter` and `lockFileURL` pointing to local paths

#### Scenario: Overriding individual modes with --standalone
- **WHEN** a developer runs `python -m webcompy generate --standalone --wasm-serving cdn`
- **THEN** `wasm_serving` SHALL be `"cdn"` (CLI flag takes precedence)
- **AND** `runtime_serving` SHALL be `"local"` (standalone default)
- **AND** `serve_all_deps` SHALL be `True` (standalone forced)
