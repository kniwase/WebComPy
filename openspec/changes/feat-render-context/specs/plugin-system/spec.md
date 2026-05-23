## MODIFIED Requirements

### Requirement: Plugin lifecycle shall support per-request initialization

`WebComPyPlugin` SHALL provide three lifecycle hooks: `on_app_init(app)` for immutable application-level setup, `on_render_context_init(ctx)` for per-request initialization (called on the server for each request, and once in the browser), and `on_app_ready(ctx)` for browser-specific initialization after DOM is available. The `on_render_context_init` hook receives a `RenderContext` and CAN register per-request DI providers. The `on_app_ready` hook signature SHALL change from `(self, app: WebComPyApp)` to `(self, ctx: RenderContext)`.

#### Scenario: Plugin with per-request DI provider
- **WHEN** a plugin defines `on_render_context_init(self, ctx)` and calls `ctx.di_scope.provide(my_key, my_request_scoped_value)`
- **AND** multiple SSR requests are processed concurrently
- **THEN** each request SHALL have its own DI provider value
- **AND** values from one request SHALL NOT leak to another request

#### Scenario: Plugin initialization during app bootstrap
- **WHEN** `WebComPyApp.__init__()` is called with `config=AppConfig(plugins=[...])`
- **THEN** `PluginManager.discover()` SHALL be called with the plugin paths
- **AND** `on_app_init(app)` SHALL be called on each plugin instance
- **AND** `on_app_init` SHALL receive the `WebComPyApp` instance (immutable definition holder)
- **AND** `on_app_init` SHALL NOT have access to a DI scope or `RenderContext`

#### Scenario: Plugin per-request initialization on the server
- **WHEN** `app.create_render_context(path)` is called
- **THEN** `on_render_context_init(ctx)` SHALL be called on each plugin instance
- **AND** `ctx` SHALL be the newly created `RenderContext`
- **AND** plugins SHALL be able to register DI providers on `ctx.di_scope`

#### Scenario: Plugin browser initialization
- **WHEN** `app.run()` is called in the browser
- **THEN** a single `RenderContext` SHALL be created
- **AND** `on_render_context_init(ctx)` SHALL be called once
- **AND** `on_app_ready(ctx)` SHALL be called once with the `RenderContext`
- **AND** `on_app_ready` SHALL have access to browser DOM APIs

#### Scenario: Backward compatibility for on_app_ready
- **WHEN** a plugin defines `on_app_ready(self, app)` with the old `WebComPyApp` signature
- **THEN** a deprecation warning SHALL be issued
- **AND** the method SHALL still be called with the `RenderContext` as the argument
- **AND** `RenderContext` SHALL duck-type-compatible with the old `WebComPyApp` interface for common properties

### Requirement: PluginManager shall initialize plugins in both app and render context phases

`PluginManager` SHALL support two initialization phases: app-level initialization (discovering plugins, calling `on_app_init`) during `WebComPyApp` creation, and render-context-level initialization (calling `on_render_context_init`, registering per-request providers) during `RenderContext` creation.

#### Scenario: Plugin initialization phases during SSR
- **WHEN** `WebComPyApp` is created
- **THEN** `PluginManager.discover()` SHALL be called
- **AND** `PluginManager.init_all()` SHALL call `on_app_init(app)` on each plugin
- **AND** static providers from `get_providers()` SHALL be collected
- **WHEN** `app.create_render_context(path)` is called
- **THEN** `on_render_context_init(ctx)` SHALL be called on each plugin instance
- **AND** per-request providers registered by plugins SHALL be available in `ctx.di_scope`

#### Scenario: Static providers are registered per RenderContext
- **WHEN** a plugin's `get_providers()` returns `{my_key: MyService}`
- **AND** `app.create_render_context(path)` is called
- **THEN** `MyService` (or its factory) SHALL be provided into the `RenderContext`'s DI scope
- **AND** the provider SHALL NOT be shared across `RenderContext` instances