# CLI — Delta: feat-pyscript-local-serving

## ADDED Requirements

### Requirement: The CLI shall download and serve PyScript/Pyodide runtime assets locally when runtime_serving is local
When `runtime_serving="local"`, the CLI SHALL download PyScript core assets (`core.js`, `core.css`) and Pyodide runtime assets (`pyodide.mjs`, `pyodide.asm.wasm`, `pyodide.asm.js`, `python_stdlib.zip`, `pyodide-lock.json`) at build time and serve them from the same origin. PyScript core assets SHALL be placed at `/_webcompy-assets/` directly. Pyodide runtime assets SHALL be placed at `/_webcompy-assets/pyodide/`.

#### Scenario: Generating a static site with local runtime serving
- **WHEN** a developer runs `python -m webcompy generate` with `AppConfig(runtime_serving="local")`
- **THEN** PyScript core assets SHALL be downloaded to `dist/_webcompy-assets/`
- **AND** Pyodide runtime assets SHALL be downloaded to `dist/_webcompy-assets/pyodide/`
- **AND** the generated HTML SHALL reference local asset URLs instead of CDN URLs

#### Scenario: Starting the dev server with local runtime serving
- **WHEN** a developer runs `python -m webcompy start --dev` with `AppConfig(runtime_serving="local")`
- **THEN** the dev server SHALL serve PyScript core assets from `/_webcompy-assets/`
- **AND** the dev server SHALL serve Pyodide runtime assets from `/_webcompy-assets/pyodide/`
- **AND** the generated HTML SHALL reference local asset URLs

#### Scenario: Runtime assets are cached
- **WHEN** a developer runs `webcompy generate` or `webcompy start` with `runtime_serving="local"`
- **THEN** downloaded runtime assets SHALL be cached at `~/.cache/webcompy/runtime-assets/{pyscript_version}/`
- **AND** cached assets with matching versions SHALL be reused without network requests

### Requirement: Downloaded runtime assets SHALL be verified against lock file hashes
When `runtime_serving="local"`, the CLI SHALL compute SHA256 hashes of all downloaded runtime assets. If the lock file contains `runtime_assets` with SHA256 hashes (from a previous build), the CLI SHALL verify downloaded files against those hashes. On mismatch, the CLI SHALL raise an error. After verification, the CLI SHALL update the lock file with the computed hashes.

#### Scenario: First build with runtime_serving="local"
- **WHEN** a developer runs `webcompy generate --runtime-serving local` for the first time
- **THEN** runtime assets SHALL be downloaded and their SHA256 hashes computed
- **AND** the lock file SHALL be updated with `runtime_assets` entries containing URLs and computed SHA256 hashes
- **AND** no hash verification SHALL be performed (no prior hashes exist)

#### Scenario: Subsequent build with runtime_serving="local"
- **WHEN** a developer runs `webcompy generate --runtime-serving local` and the lock file contains `runtime_assets` with SHA256 hashes
- **THEN** downloaded runtime assets SHALL be verified against the lock file hashes
- **AND** on hash mismatch, the CLI SHALL raise an error
- **AND** the lock file SHALL be updated with the newly computed hashes

### Requirement: Temporary directories used for runtime asset downloads SHALL be cleaned up
When `webcompy generate` or `webcompy start` creates temporary directories for runtime asset downloads, those directories SHALL be cleaned up after use.

#### Scenario: Temporary directory cleanup after static site generation
- **WHEN** `webcompy generate --runtime-serving local` completes
- **THEN** any temporary directories created for runtime asset downloads SHALL be removed

#### Scenario: Temporary directory cleanup after dev server shutdown
- **WHEN** `webcompy start --dev --runtime-serving local` terminates
- **THEN** any temporary directories created for runtime asset downloads SHALL be removed

### Requirement: Runtime-local HTML shall reference local runtime asset URLs and configure PyScript for local Pyodide
In runtime-local mode, `generate_html()` SHALL replace PyScript and Pyodide CDN URLs with same-origin paths under `/_webcompy-assets/`. The PyScript `py-config` SHALL include `interpreter` and `lockFileURL` pointing to local Pyodide assets.

#### Scenario: Runtime-local PyScript script tag
- **WHEN** runtime-local mode is enabled
- **THEN** the `<script type="module" src="...">` tag SHALL reference `/_webcompy-assets/core.js`
- **AND** the CSS link SHALL reference `/_webcompy-assets/core.css`

#### Scenario: Runtime-local Pyodide interpreter configuration
- **WHEN** runtime-local mode is enabled
- **THEN** `py-config` SHALL include `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"`

#### Scenario: Runtime-local lock file URL
- **WHEN** runtime-local mode is enabled
- **THEN** `py-config` SHALL include `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"`

#### Scenario: Non-runtime-local HTML is unchanged
- **WHEN** `runtime_serving="cdn"` (default)
- **THEN** `py-config` SHALL NOT include `interpreter` or `lockFileURL`
- **AND** script and CSS tags SHALL reference CDN URLs

### Requirement: The CLI shall accept --runtime-serving value flag
The `start` and `generate` CLI subcommands SHALL accept `--runtime-serving <mode>` where `<mode>` is `"cdn"` or `"local"`. This overrides `AppConfig.runtime_serving`.

#### Scenario: Overriding with --runtime-serving local
- **WHEN** a developer runs `python -m webcompy start --dev --runtime-serving local`
- **THEN** `runtime_serving` SHALL be `"local"` for the session

#### Scenario: Overriding with --runtime-serving cdn
- **WHEN** a developer runs `python -m webcompy generate --runtime-serving cdn`
- **THEN** `runtime_serving` SHALL be `"cdn"` for the session

## MODIFIED Requirements

### Requirement: Generated HTML shall include PyScript bootstrapping
The PyScript configuration SHALL include `interpreter` and `lockFileURL` fields when `runtime_serving="local"`. When `runtime_serving="cdn"` (default), these fields SHALL NOT be included. When `wasm_serving="local"` and `runtime_serving="cdn"`, `lockFileURL` SHALL be set to the CDN `pyodide-lock.json` URL (as defined in `feat-wasm-local-serving`).

#### Scenario: Inspecting generated HTML with runtime_serving="local"
- **WHEN** `AppConfig(runtime_serving="local")` and a generated `index.html` is examined
- **THEN** `py-config` SHALL include `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"`
- **AND** `py-config` SHALL include `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"`
- **AND** the script tag SHALL reference `/_webcompy-assets/core.js`
- **AND** the CSS link SHALL reference `/_webcompy-assets/core.css`

#### Scenario: Inspecting generated HTML with runtime_serving="cdn" and wasm_serving="local"
- **WHEN** `AppConfig(runtime_serving="cdn", wasm_serving="local")`
- **THEN** `py-config` SHALL NOT include `interpreter`
- **AND** `py-config` SHALL include `lockFileURL` pointing to the CDN `pyodide-lock.json` URL
- **AND** the script tag and CSS link SHALL reference CDN URLs

#### Scenario: Inspecting generated HTML with runtime_serving="cdn" and wasm_serving="cdn"
- **WHEN** `AppConfig(runtime_serving="cdn", wasm_serving="cdn")` (defaults)
- **THEN** `py-config` SHALL NOT include `interpreter`
- **AND** `py-config` SHALL NOT include `lockFileURL`
