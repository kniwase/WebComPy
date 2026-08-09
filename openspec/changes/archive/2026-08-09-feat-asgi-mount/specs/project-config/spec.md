# Delta Spec: project-config

## ADDED Requirements

### Requirement: WebComPyServerConfig shall support ASGI mounts
`WebComPyServerConfig` SHALL provide a `mounts` field of type `Callable[[], dict[str, ASGIApp]] | None` defaulting to `None`. The callable form SHALL defer import and construction of user ASGI apps until server startup, so that importing `webcompy_config.py` does not import server-only application code. The field is server-only configuration and SHALL NOT affect browser-relevant config (`WebComPyAppConfig`).

#### Scenario: Declaring mounts lazily
- **WHEN** a project sets `WebComPyServerConfig(mounts=lambda: {"/api": api_app})` in `webcompy_config.py`
- **THEN** importing the config module SHALL NOT import `api_app`
- **AND** the callable SHALL be invoked when the serving app is constructed

#### Scenario: Default configuration unchanged
- **WHEN** `WebComPyServerConfig()` is constructed without `mounts`
- **THEN** `mounts` SHALL be `None` and serving behavior SHALL be unchanged
