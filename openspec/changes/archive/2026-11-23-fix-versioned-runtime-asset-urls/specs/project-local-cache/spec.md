# Project-Local Cache

## MODIFIED Requirements

### Requirement: The dev server shall serve runtime and WASM assets from disk
When `runtime_serving="local"` or `wasm_serving="local"`, the dev server SHALL serve assets directly from the project-local cache directory using `FileResponse` (or equivalent disk-based streaming), rather than loading file contents into memory with `read_bytes()`. Local runtime assets SHALL be routed at `/_webcompy-assets/{pyscript_version}/...`, while local WASM wheels SHALL remain routed at `/_webcompy-assets/packages/{file_name}`.

#### Scenario: Serving a local runtime asset
- **WHEN** a browser requests `/_webcompy-assets/{pyscript_version}/core.js`
- **AND** `runtime_serving="local"`
- **THEN** the server SHALL stream the file from `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/core.js`
- **AND** the file SHALL NOT be fully loaded into memory before the response begins

#### Scenario: Serving a local WASM wheel
- **WHEN** a browser requests `/_webcompy-assets/packages/{file_name}`
- **AND** `wasm_serving="local"`
- **THEN** the server SHALL stream the file from `{app_package_path}/.webcompy_modules/pyodide-packages/{pyodide_version}/{file_name}`
- **AND** the file SHALL NOT be fully loaded into memory before the response begins

### Requirement: Static site generation shall copy from project-local cache to dist
During `webcompy generate`, runtime assets SHALL be copied directly from `.webcompy_modules/` to `dist/_webcompy-assets/{pyscript_version}/` and WASM wheels SHALL be copied to `dist/_webcompy-assets/packages/`. No temporary directories SHALL be created for this purpose.

#### Scenario: Generating with local runtime serving
- **WHEN** a developer runs `python -m webcompy generate --runtime-serving local`
- **THEN** runtime assets SHALL be copied from `{app_package_path}/.webcompy_modules/runtime-assets/{pyscript_version}/` to `dist/_webcompy-assets/{pyscript_version}/`
- **AND** no temporary directory SHALL be created for runtime asset staging

#### Scenario: Generating with local WASM serving
- **WHEN** a developer runs `python -m webcompy generate --wasm-serving local`
- **THEN** WASM wheels SHALL be copied from `{app_package_path}/.webcompy_modules/pyodide-packages/{pyodide_version}/` to `dist/_webcompy-assets/packages/`
- **AND** no temporary directory SHALL be created for wheel staging
