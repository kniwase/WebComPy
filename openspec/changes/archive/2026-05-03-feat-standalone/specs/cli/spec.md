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

### Requirement: The CLI shall support switching between standalone and non-standalone modes across invocations
Each CLI invocation creates a fresh `AppConfig` instance. The `--standalone` and `--no-standalone` CLI flags SHALL toggle all local-serving modes simultaneously in the new execution context. Switching from standalone to non-standalone mode across invocations SHALL revert the derived defaults to their non-standalone values. Explicitly set individual flags in the current invocation SHALL take precedence over standalone defaults.

#### Scenario: Switching from non-standalone to standalone across invocations
- **WHEN** a developer previously ran `python -m webcompy generate` (non-standalone) and then runs `python -m webcompy generate --standalone`
- **THEN** a fresh `AppConfig` SHALL be created with `standalone=True`
- **AND** the lock file SHALL be regenerated with `standalone: true`, `wasm_serving: "local"`, `runtime_serving: "local"`
- **AND** all runtime and WASM assets SHALL be downloaded and served locally

#### Scenario: Switching from standalone to non-standalone across invocations
- **WHEN** a developer previously ran `python -m webcompy generate --standalone` and then runs `python -m webcompy generate --no-standalone`
- **THEN** a fresh `AppConfig` SHALL be created with `standalone=False`
- **AND** the lock file SHALL be regenerated with `standalone: false`, `wasm_serving: "cdn"`, `runtime_serving: "cdn"`
- **AND** runtime and WASM assets SHALL NOT be downloaded
- **AND** `py-config` SHALL reference CDN URLs for the PyScript/Pyodide runtime

#### Scenario: Explicit overrides in the current invocation take precedence
- **WHEN** a developer runs `python -m webcompy generate --standalone --wasm-serving cdn`
- **THEN** `wasm_serving` SHALL be `"cdn"` (CLI flag takes precedence)
- **AND** `runtime_serving` SHALL be `"local"` (standalone default)
