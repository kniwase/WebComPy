# Delta Spec: server-fetch-asgi

## ADDED Requirements

### Requirement: ServerFetchPort shall support binding to a root ASGI app
`ServerFetchPort` SHALL support being configured against a root ASGI application that is distinct from WebComPy's internal serving app (embedded deployments). `configure_server_context()` SHALL accept an optional `root_app` parameter; when provided, self-site fetch dispatch SHALL target `root_app` instead of the internal serving app. When `root_app` is `None` (default), behavior SHALL be exactly as before. The mechanism SHALL prevent double-configuration conflicts when the CLI also configures the port (either by deferring the CLI's configuration or by an explicit rebind path).

#### Scenario: root_app provided
- **WHEN** `configure_server_context(app, root_app=host)` is called and the serving app is mounted into `host`
- **THEN** self-site fetches during SSR SHALL be dispatched through `host` via ASGI transport

#### Scenario: Default binding unchanged
- **WHEN** `configure_server_context(app)` is called without `root_app`
- **THEN** self-site fetches SHALL be dispatched through WebComPy's internal serving app as before this change
