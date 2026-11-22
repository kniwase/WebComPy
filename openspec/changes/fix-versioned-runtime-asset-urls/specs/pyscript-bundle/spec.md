# PyScript Bundle

## MODIFIED Requirements

### Requirement: The framework shall serve PyScript core bundle files at the correct paths

All PyScript core bundle files SHALL be served from the versioned `_webcompy-assets/{PYSCRIPT_VERSION}/` path prefix (SSG) or `/_webcompy-assets/{PYSCRIPT_VERSION}/` URL prefix (dev/prod ASGI server), preserving the flat directory structure so that relative `import()` paths within the bundle resolve correctly.

#### Scenario: SSG output includes all PyScript core bundle files

- **WHEN** `generate_static_site()` is called with `runtime_serving="local"`
- **THEN** all PyScript core bundle `.js` and `.css` files SHALL be placed in `dist/_webcompy-assets/{PYSCRIPT_VERSION}/`
- **AND** `dist/_webcompy-assets/{PYSCRIPT_VERSION}/core.js` and the hashed core module chunk imported by `core.js` (for example `core-7nKZylPm.js` in PyScript `2026.7.3`) SHALL both exist
- **AND** relative imports from `core.js` to that hashed core module chunk SHALL resolve correctly
- **AND** unversioned `dist/_webcompy-assets/core.js` SHALL NOT exist

#### Scenario: Dev server serves all PyScript core bundle files

- **WHEN** `create_asgi_app()` is called with `runtime_serving="local"`
- **THEN** all PyScript core bundle `.js` and `.css` files SHALL be served at `/_webcompy-assets/{PYSCRIPT_VERSION}/{filename}`
- **AND** requesting `/_webcompy-assets/{PYSCRIPT_VERSION}/<core-chunk>.js` imported by `core.js` SHALL return HTTP 200 with the correct content

### Requirement: The HTML shall reference the local core.js with the correct path

The generated HTML SHALL reference local runtime assets under `{base_url}_webcompy-assets/{PYSCRIPT_VERSION}/` when `runtime_serving="local"` (default `base_url="/"` yields `/_webcompy-assets/{PYSCRIPT_VERSION}/...`). This keeps HTML entry references atomic with the pinned PyScript and Pyodide version across deployments.

#### Scenario: HTML references local core.js

- **WHEN** `runtime_serving="local"` and HTML is generated
- **THEN** the `<script type="module">` tag SHALL reference `{base_url}_webcompy-assets/{PYSCRIPT_VERSION}/core.js`
- **AND** the `<link rel="stylesheet">` tag SHALL reference `{base_url}_webcompy-assets/{PYSCRIPT_VERSION}/core.css`
- **AND** `py-config` SHALL set `interpreter` to `{base_url}_webcompy-assets/{PYSCRIPT_VERSION}/pyodide/pyodide.mjs` and `lockFileURL` to `{base_url}_webcompy-assets/{PYSCRIPT_VERSION}/pyodide/pyodide-lock.json`

## ADDED Requirements

### Requirement: The ASGI server shall set versioned cache headers for local runtime assets

When `create_asgi_app()` serves local runtime assets from `/_webcompy-assets/{PYSCRIPT_VERSION}/{filename:path}`, responses in production mode (`mode="prod"`) SHALL include `Cache-Control: public, max-age=31536000, immutable`, and responses in development mode (`mode="dev"`) SHALL include `Cache-Control: max-age=86400, must-revalidate`. Requests to unversioned `/_webcompy-assets/core.js` or a mismatched runtime version SHALL NOT be served as runtime assets.

#### Scenario: Production server sets immutable Cache-Control header on runtime assets

- **WHEN** `create_asgi_app()` is created with `mode="prod"` and `runtime_serving="local"`
- **AND** a client requests `GET /_webcompy-assets/{PYSCRIPT_VERSION}/core.js`
- **THEN** the response status SHALL be `200`
- **AND** the `Cache-Control` header SHALL be `public, max-age=31536000, immutable`

#### Scenario: Dev server sets revalidating Cache-Control header on runtime assets

- **WHEN** `create_asgi_app()` is created with `mode="dev"` and `runtime_serving="local"`
- **AND** a client requests `GET /_webcompy-assets/{PYSCRIPT_VERSION}/core.js`
- **THEN** the response status SHALL be `200`
- **AND** the `Cache-Control` header SHALL be `max-age=86400, must-revalidate`

#### Scenario: Unversioned or mismatched runtime asset URL is rejected

- **WHEN** `create_asgi_app()` is created with `runtime_serving="local"`
- **AND** a client requests `GET /_webcompy-assets/core.js` or `GET /_webcompy-assets/2026.3.1/core.js` (when `PYSCRIPT_VERSION` is `2026.7.3`)
- **THEN** the runtime asset route SHALL NOT match and SHALL NOT return JavaScript asset content
