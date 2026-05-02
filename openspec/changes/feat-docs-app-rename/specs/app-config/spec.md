## ADDED Requirements

### Requirement: Docs_app server config shall include static file serving
The docs_app `webcompy_server_config.py` SHALL configure `static_files_dir="static"` in both `ServerConfig` and `GenerateConfig` so that static assets (such as JSON data files) are served correctly by the dev server and included in the generated static site.

#### Scenario: Dev server serving static files
- **WHEN** the docs_app dev server is running with `static_files_dir="static"`
- **AND** a browser requests `/fetch_sample/sample.json`
- **THEN** the server SHALL return the JSON file from `docs_app/static/fetch_sample/sample.json`

#### Scenario: Static site generation including static files
- **WHEN** a developer runs `webcompy generate --app docs_app.bootstrap:app`
- **AND** `GenerateConfig` includes `static_files_dir="static"`
- **THEN** the generated static site SHALL include the contents of `docs_app/static/` in its output
