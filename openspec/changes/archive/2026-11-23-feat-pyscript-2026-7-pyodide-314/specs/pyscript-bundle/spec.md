# Spec Delta

## ADDED Requirements

### Requirement: The framework shall resolve version-appropriate Pyodide runtime asset filenames

When downloading, caching, serving locally, or recording Pyodide runtime assets in `webcompy-lock.json`, the framework SHALL select the runtime entry script filename according to the target Pyodide version alongside `pyodide.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, and `pyodide-lock.json`. Pyodide versions `< 0.30` (such as `0.29.3`) SHALL resolve `pyodide.asm.js`. Pyodide versions `>= 0.30` (including `314.x` releases such as `314.0.3`) SHALL resolve `pyodide.asm.mjs`. Both `.js` and `.mjs` runtime assets SHALL be served with a JavaScript media type when served locally.

#### Scenario: Pyodide 314.0.3 resolves pyodide.asm.mjs

- **WHEN** local runtime assets are downloaded or recorded in a lockfile for Pyodide `314.0.3`
- **THEN** the resolved asset set SHALL include `pyodide.asm.mjs` alongside `pyodide.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, and `pyodide-lock.json`
- **AND** `pyodide.asm.js` SHALL NOT be requested or included

#### Scenario: Pyodide 0.29.3 retains pyodide.asm.js

- **WHEN** local runtime assets are downloaded or recorded in a lockfile for Pyodide `0.29.3` (for example during a version-bump sweep against `2026.3.1`)
- **THEN** the resolved asset set SHALL include `pyodide.asm.js` alongside `pyodide.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, and `pyodide-lock.json`
- **AND** `pyodide.asm.mjs` SHALL NOT be requested or included

## MODIFIED Requirements

### Requirement: The framework shall serve PyScript core bundle files at the correct paths

All PyScript core bundle files SHALL be served from the `_webcompy-assets/` path prefix (SSG) or `/_webcompy-assets/` URL prefix (dev server), preserving the flat directory structure so that relative `import()` paths within the bundle resolve correctly.

#### Scenario: SSG output includes all PyScript core bundle files

- **WHEN** `generate_static_site()` is called with `runtime_serving="local"`
- **THEN** all PyScript core bundle `.js` and `.css` files SHALL be placed in `dist/_webcompy-assets/`
- **AND** `dist/_webcompy-assets/core.js` and the hashed core module chunk imported by `core.js` (for example `core-7nKZylPm.js` in PyScript `2026.7.3`) SHALL both exist
- **AND** relative imports from `core.js` to that hashed core module chunk SHALL resolve correctly

#### Scenario: Dev server serves all PyScript core bundle files

- **WHEN** `create_asgi_app()` is called with `runtime_serving="local"`
- **THEN** all PyScript core bundle `.js` and `.css` files SHALL be served at `/_webcompy-assets/{filename}`
- **AND** requesting `/_webcompy-assets/<core-chunk>.js` imported by `core.js` SHALL return HTTP 200 with the correct content
