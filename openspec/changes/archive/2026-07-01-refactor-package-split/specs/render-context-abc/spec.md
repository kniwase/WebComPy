# Render Context ABC

## Purpose

`RenderContext` is refactored into an abstract base class, allowing environment-specific port provisioning to be implemented by subclasses (`BrowserRenderContext` in core, `ServerRenderContext` in `webcompy-server`) without core importing server-side port implementations. This breaks the last direct coupling between core and server code.

## Requirements

### Requirement: RenderContext shall be an abstract base class

`RenderContext` SHALL be an ABC with an abstract method `_register_ports(self) -> None`. All shared initialization logic (DI scope creation, ComponentStore, Router, plugins, theme initialization, deferred ops) SHALL remain in the base `__init__`. The base `__init__` SHALL accept `initial_theme` and `cookie_header` keyword arguments (added in main #178). Port provisioning SHALL be delegated to `_register_ports()`.

#### Scenario: RenderContext base __init__ contains shared logic
- **WHEN** any `RenderContext` subclass is instantiated
- **THEN** a `DIScope` SHALL be created and entered
- **AND** a `ComponentStore` SHALL be created and provided into the DI scope
- **AND** a `Router` SHALL be created if the app has one
- **AND** `self._initial_theme` and `self._cookie_header` SHALL be stored from constructor kwargs
- **AND** `_register_ports()` SHALL be called (subclass hook)
- **AND** theme initialization (`ThemeManager`, `THEME_KEY`) SHALL run after port provisioning
- **AND** plugins SHALL be initialized via `app._plugin_manager.init_render_context(self)`
- **AND** `AppDocumentRoot` SHALL be created
- **AND** deferred operations SHALL be applied

#### Scenario: Subclass must implement _register_ports
- **WHEN** a subclass does not implement `_register_ports`
- **THEN** instantiation SHALL fail with `TypeError` (standard ABC behavior)

### Requirement: BrowserRenderContext shall provision Browser*Port instances

`BrowserRenderContext(RenderContext)` SHALL implement `_register_ports()` by importing and providing all seven `Browser*Port` implementations (`BrowserDOMPort`, `BrowserFetchPort`, `BrowserFFIPort`, `BrowserHistoryPort`, `BrowserHostPort`, `BrowserCookiePort`, `BrowserMediaQueryPort`) into the DI scope.

#### Scenario: BrowserRenderContext provisions all ports
- **WHEN** `BrowserRenderContext` is instantiated in the browser environment (`ENVIRONMENT == "pyscript"`)
- **THEN** `inject(DOM_PORT_KEY)` SHALL return a `BrowserDOMPort`
- **AND** `inject(FETCH_PORT_KEY)` SHALL return a `BrowserFetchPort`
- **AND** `inject(FFI_PORT_KEY)` SHALL return a `BrowserFFIPort`
- **AND** `inject(HISTORY_PORT_KEY)` SHALL return a `BrowserHistoryPort`
- **AND** `inject(HOST_PORT_KEY)` SHALL return a `BrowserHostPort`
- **AND** `inject(COOKIE_PORT_KEY)` SHALL return a `BrowserCookiePort`
- **AND** `inject(MEDIA_QUERY_PORT_KEY)` SHALL return a `BrowserMediaQueryPort`

#### Scenario: BrowserRenderContext raises on render_html
- **WHEN** `BrowserRenderContext.render_html()` is called
- **THEN** `WebComPyException` SHALL be raised with a message indicating `render_html` is not available in the browser

### Requirement: ServerRenderContext shall be provided by webcompy-server

`ServerRenderContext(RenderContext)` SHALL be defined in `webcompy-server` (not in core). It SHALL implement `_register_ports()` by providing all seven `Server*Port` implementations. It SHALL implement `render_html()` as an `async def` using `webcompy_server._html.generate_html()`. `ServerCookiePort` SHALL receive `self._cookie_header` from the base `__init__`.

#### Scenario: ServerRenderContext provisions server ports
- **WHEN** `ServerRenderContext` is instantiated on the server
- **THEN** `inject(DOM_PORT_KEY)` SHALL return a `ServerDOMPort`
- **AND** `inject(FETCH_PORT_KEY)` SHALL return a `ServerFetchPort`
- **AND** `inject(FFI_PORT_KEY)` SHALL return a `ServerFFIPort`
- **AND** `inject(HISTORY_PORT_KEY)` SHALL return a `ServerHistoryPort`
- **AND** `inject(HOST_PORT_KEY)` SHALL return a `ServerHostPort`
- **AND** `inject(COOKIE_PORT_KEY)` SHALL return a `ServerCookiePort` initialized with `cookie_header`
- **AND** `inject(MEDIA_QUERY_PORT_KEY)` SHALL return a `ServerMediaQueryPort`

#### Scenario: ServerRenderContext produces HTML
- **WHEN** `await ctx.render_html(app_package_name="myapp", ...)` is called on a `ServerRenderContext`
- **THEN** full SSR HTML SHALL be returned as a string

### Requirement: WebComPyApp shall accept an injectable RenderContext class

`WebComPyApp.__init__` SHALL accept an optional `_render_context_class: type[RenderContext] | None` parameter (default `None`). `WebComPyApp.create_render_context()` SHALL use `self._render_context_class` if set, otherwise fall back to `BrowserRenderContext`. An underscore prefix SHALL denote this as internal API.

#### Scenario: Default behavior uses BrowserRenderContext
- **WHEN** `app = WebComPyApp(root_component=MyRoot)` is created without `_render_context_class`
- **AND** `app.create_render_context()` is called
- **THEN** a `BrowserRenderContext` SHALL be created

#### Scenario: Injected class overrides default
- **WHEN** `app._render_context_class = ServerRenderContext`
- **AND** `app.create_render_context()` is called
- **THEN** a `ServerRenderContext` SHALL be created

### Requirement: webcompy-server shall provide a configure_server_context helper

`webcompy_server` SHALL export a function `configure_server_context(app: WebComPyApp) -> None` that sets `app._render_context_class = ServerRenderContext`. CLI and testing code SHALL call this function before using `app.create_render_context()`.

#### Scenario: Configuring server context before SSR
- **WHEN** `configure_server_context(app)` is called
- **AND** `app.create_render_context("/path")` is subsequently called
- **THEN** a `ServerRenderContext` SHALL be created
- **AND** `ctx.render_html(...)` SHALL produce valid HTML
