## ADDED Requirements

### Requirement: The dev/prod SSR server SHALL expose a `GET {base_url}_webcompy-resource/{path:path}` endpoint

`create_asgi_app` in `webcompy_cli._server` SHALL register a Starlette route `GET {base_url}_webcompy-resource/{path:path}` that serves allow-listed application resource files. The endpoint SHALL be registered in both dev and prod modes (live SSR server).

The handler SHALL:
1. Reject requests for paths outside the precomputed allow-list with HTTP 404.
2. Compute the resolved filesystem path as `(app_package_path / path).resolve()` and verify containment inside `app_package_path` (rejecting any path that escapes via `..` or symlink traversal) with HTTP 403 if containment fails.
3. Read the file on every request (no caching).
4. Return the file content with a `Content-Type` derived from `mimetypes.guess_type(path)` (falling back to `application/octet-stream`) and `Cache-Control: no-cache` in dev mode, `Cache-Control: public, max-age=3600` in prod mode.

#### Scenario: Allow-listed resource is served
- **WHEN** the allow-list contains `"templates/card.html"` and the file exists
- **AND** a GET request arrives for `{base_url}_webcompy-resource/templates/card.html`
- **THEN** the response SHALL be HTTP 200 with the file's UTF-8 text body and `Content-Type: text/html`

#### Scenario: Non-allow-listed resource returns 404
- **WHEN** the allow-list does NOT contain `"secrets/credentials.json"`
- **AND** a GET request arrives for `{base_url}_webcompy-resource/secrets/credentials.json`
- **THEN** the response SHALL be HTTP 404
- **AND** no filesystem access SHALL occur

#### Scenario: Path traversal rejected
- **WHEN** a GET request arrives for `{base_url}_webcompy-resource/../webcompy_config.py`
- **THEN** the response SHALL be HTTP 404 (resolved outside allow-list) or 403 (realpath outside root)
- **AND** the file SHALL NOT be returned

#### Scenario: Cache-Control in dev mode
- **WHEN** the server runs in dev mode
- **THEN** resource responses SHALL include `Cache-Control: no-cache`

#### Scenario: Cache-Control in prod mode
- **WHEN** the server runs in prod mode
- **THEN** resource responses SHALL include `Cache-Control: public, max-age=3600`

### Requirement: `generate_static_site` SHALL copy allow-listed resources to `dist/_webcompy-resource/{path}`

`generate_static_site` in `webcompy_cli._generate` SHALL copy every allow-listed resource to `{dist_dir}/_webcompy-resource/{path}` preserving the package-relative path's directory structure. The copy SHALL happen after the dist directory is created and before static-file and app-package copies.

#### Scenario: Allow-listed resources appear in dist
- **WHEN** the allow-list contains `"templates/card.html"`, `"assets/icons/star.svg"`, and `"styles/main.css"`
- **AND** `generate_static_site(app)` runs
- **THEN** `{dist_dir}/_webcompy-resource/templates/card.html` SHALL exist
- **AND** `{dist_dir}/_webcompy-resource/assets/icons/star.svg` SHALL exist
- **AND** `{dist_dir}/_webcompy-resource/styles/main.css` SHALL exist
- **AND** each file's contents SHALL match the source

#### Scenario: Non-allow-listed files are not copied
- **WHEN** the app package contains `secrets/credentials.json` and `webcompy_config.py`
- **AND** these paths are NOT in the allow-list
- **THEN** `{dist_dir}/_webcompy-resource/secrets/credentials.json` SHALL NOT exist
- **AND** `{dist_dir}/_webcompy-resource/webcompy_config.py` SHALL NOT exist

#### Scenario: Static host serves the same URL
- **WHEN** the generated `dist/` directory is deployed to a static host
- **AND** a browser fetches `{base_url}_webcompy-resource/templates/card.html`
- **THEN** the host SHALL serve the copied file with the same content as the live SSR endpoint would have
