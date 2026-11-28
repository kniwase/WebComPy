# Spec Delta

## ADDED Requirements

### Requirement: Production ASGI server shall emit immutable cache headers for content-hashed and version-tagged wheels

When `create_asgi_app()` serves application or framework wheels from `/_webcompy-app-package/{filename:path}` or local WASM package wheels from `/_webcompy-assets/packages/{filename:path}`, responses in production mode (`mode="prod"`) SHALL include `Cache-Control: public, max-age=31536000, immutable`. In development mode (`mode="dev"`), `/_webcompy-app-package/*` SHALL retain its existing dev cache headers (`Cache-Control: max-age=86400, must-revalidate` for the framework wheel in split mode and `Cache-Control: no-cache` for the app wheel), and `/_webcompy-assets/packages/*` SHALL include `Cache-Control: max-age=86400, must-revalidate`.

#### Scenario: Production server marks app and framework wheels immutable

- **WHEN** `create_asgi_app()` is created with `mode="prod"`
- **AND** a client requests a built wheel under `/_webcompy-app-package/`
- **THEN** the response status SHALL be `200`
- **AND** the `Cache-Control` header SHALL be `public, max-age=31536000, immutable`

#### Scenario: Production server marks local WASM wheels immutable

- **WHEN** `create_asgi_app()` is created with `mode="prod"` and `wasm_serving="local"`
- **AND** a client requests a WASM wheel under `/_webcompy-assets/packages/`
- **THEN** the response status SHALL be `200`
- **AND** the `Cache-Control` header SHALL be `public, max-age=31536000, immutable`

#### Scenario: Dev server preserves revalidating cache headers for WASM wheels

- **WHEN** `create_asgi_app()` is created with `mode="dev"` and `wasm_serving="local"`
- **AND** a client requests a WASM wheel under `/_webcompy-assets/packages/`
- **THEN** the response status SHALL be `200`
- **AND** the `Cache-Control` header SHALL be `max-age=86400, must-revalidate`

### Requirement: Production SSR and SSG builds shall cache-bust framework UI and static assets via content hashes

When building artifacts with `dev_mode=False` (production `create_asgi_app(..., mode="prod")` and `generate_static_site()`), the CLI SHALL compute deterministic 8-character lowercase hexadecimal SHA-256 content hashes for all bundled framework UI stylesheets (`webcompy.ui._styles`) and all files under `static_files_dir`:

- Every stylesheet in `webcompy.ui._styles` except `index.css` SHALL be hashed first, any relative `@import url("./<file>");` rules inside `index.css` SHALL be rewritten to `./<file>?v=<hash>`, and `index.css`'s own hash SHALL be computed from the rewritten `index.css` bytes. Source package resources returned by `webcompy.ui._styles.get_styles_file()` / `get_styles_files()` SHALL remain unmutated.
- `create_asgi_app(..., mode="prod")` SHALL serve the rewritten `index.css` bytes at `/_webcompy-ui/index.css` and SHALL set `Cache-Control: public, max-age=0, must-revalidate` on `/_webcompy-ui/{filename}` (`Cache-Control: no-cache, must-revalidate` in `dev_mode=True`).
- `generate_static_site()` SHALL write the rewritten `index.css` bytes to `dist/_webcompy-ui/index.css`.
- `generate_html()` SHALL accept an optional `asset_hashes` mapping and, when supplied, SHALL append `?v=<hash>` (preserving any existing query parameters via `&v=<hash>` and preserving `#fragment`) to the auto-injected `/_webcompy-ui/index.css` link and to any matching same-origin `<link href>` in `<head>` or external `<script src>`, leaving external/scheme URLs, unknown paths, and URLs already specifying a `v` query parameter unchanged.
- In `dev_mode=True`, `asset_hashes` SHALL be disabled (`None`) so HTML and `/_webcompy-ui/index.css` remain unversioned for live iteration.

#### Scenario: Production SSR HTML and framework index.css carry content hashes

- **WHEN** `create_asgi_app()` is constructed with `mode="prod"` for an app linking `/styles/components.css` and `/_webcompy-ui/prose.css`
- **THEN** rendered HTML SHALL contain `?v=<hash>` query strings matching each file's 8-character SHA-256 digest on `/_webcompy-ui/index.css`, `/_webcompy-ui/prose.css`, and `/styles/components.css`
- **AND** requesting `GET /_webcompy-ui/index.css` SHALL return `Cache-Control: public, max-age=0, must-revalidate` with `?v=<hash>` appended to every `@import url("./...")` rule

#### Scenario: Leaf UI stylesheet edits invalidate index.css hash

- **WHEN** a stylesheet imported by `index.css` changes while `index.css` itself is untouched on disk
- **THEN** both that stylesheet's `?v=` hash inside the rewritten `index.css` and `index.css`'s own computed `?v=` hash SHALL change

#### Scenario: Static site generation emits hashed references and rewritten index.css

- **WHEN** `generate_static_site()` builds an application
- **THEN** `dist/_webcompy-ui/index.css` SHALL contain `?v=<hash>` on each imported stylesheet
- **AND** generated HTML files SHALL reference `/_webcompy-ui/index.css?v=<hash>` and `?v=<hash>` for static assets listed in `<head>`

#### Scenario: Development server skips cache-busting query strings

- **WHEN** `create_asgi_app()` is constructed with `mode="dev"`
- **THEN** rendered HTML SHALL NOT append `?v=` hashes to `/_webcompy-ui/index.css` or static `<link>`/`<script>` references
- **AND** `GET /_webcompy-ui/index.css` SHALL return the unrewritten `@import` rules with `Cache-Control: no-cache, must-revalidate`
