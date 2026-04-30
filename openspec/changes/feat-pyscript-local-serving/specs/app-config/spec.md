# Application Configuration — Delta: feat-pyscript-local-serving

## ADDED Requirements

### Requirement: AppConfig shall include a runtime_serving field for controlling PyScript/Pyodide runtime delivery
`AppConfig` SHALL include a `runtime_serving: Literal["cdn", "local"] = "cdn"` field. When `"cdn"` (default), the PyScript runtime (`core.js`, `core.css`) and the Pyodide engine (`pyodide.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, `pyodide-lock.json`) are loaded from their respective CDNs. When `"local"`, all runtime assets are downloaded at build time and served from the same origin.

#### Scenario: Default CDN mode
- **WHEN** a developer creates `AppConfig()` without `runtime_serving`
- **THEN** PyScript and Pyodide runtime assets SHALL be loaded from CDN URLs

#### Scenario: Local runtime serving mode
- **WHEN** a developer creates `AppConfig(runtime_serving="local")`
- **THEN** all PyScript and Pyodide runtime assets SHALL be downloaded at build time
- **AND** PyScript core assets SHALL be served from `/_webcompy-assets/` and Pyodide runtime assets SHALL be served from `/_webcompy-assets/pyodide/`
- **AND** `py-config` SHALL include `interpreter` pointing to `/_webcompy-assets/pyodide/pyodide.mjs`
- **AND** `py-config` SHALL include `lockFileURL` pointing to `/_webcompy-assets/pyodide/pyodide-lock.json`

## MODIFIED Requirements

### Requirement: ServerConfig and GenerateConfig shall NOT include runtime serving fields
`runtime_serving` is on `AppConfig`, not `ServerConfig` or `GenerateConfig`. The runtime serving mode is a property of the application, not of the server or SSG configuration. CLI flags (`--runtime-serving`) SHALL override `AppConfig.runtime_serving`, similar to how `--serve-all-deps` overrides `AppConfig.serve_all_deps`.