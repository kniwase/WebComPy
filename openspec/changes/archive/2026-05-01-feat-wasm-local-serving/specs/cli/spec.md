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

### Requirement: The CLI shall set lockFileURL in py-config when WASM packages are served locally
When `wasm_serving="local"`, the generated HTML SHALL include `lockFileURL` in `py-config` so that Pyodide/micropip can resolve transitive dependencies between WASM packages. The `lockFileURL` SHALL point to the Pyodide CDN URL for the lock file. If `runtime_serving="local"` is also set (from `feat-pyscript-local-serving`), the `lockFileURL` SHALL point to the local `pyodide-lock.json` instead.

#### Scenario: lockFileURL set to CDN URL when wasm_serving is local
- **WHEN** `wasm_serving="local"` and `runtime_serving="cdn"` (default)
- **THEN** `py-config.lockFileURL` SHALL be set to `https://cdn.jsdelivr.net/pyodide/v{pyodide_version}/full/pyodide-lock.json`

#### Scenario: lockFileURL set to local URL when runtime_serving is also local
- **WHEN** `wasm_serving="local"` and `runtime_serving="local"`
- **THEN** `py-config.lockFileURL` SHALL be set to `/_webcompy-assets/pyodide/pyodide-lock.json`
