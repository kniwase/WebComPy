## ADDED Requirements

### Requirement: The application shall provide a browser entry point via app.run()
In the browser environment, `app.run(selector)` SHALL mount and render the application into the DOM element matching the given CSS selector. The `selector` parameter SHALL default to `"#webcompy-app"` for backward compatibility.

#### Scenario: Running an app with default selector
- **WHEN** a developer calls `app.run()` in the browser
- **THEN** the application SHALL mount into the element with `id="webcompy-app"`
- **AND** pre-rendered DOM nodes SHALL be hydrated
- **AND** the loading indicator SHALL be removed after the first render

#### Scenario: Running an app with custom selector
- **WHEN** a developer calls `app.run("#my-container")` in the browser
- **THEN** the application SHALL mount into the element matching `#my-container`
- **AND** all reactivity, routing, and head management SHALL work as if mounted at the default selector

#### Scenario: Calling run() in a non-browser environment
- **WHEN** a developer calls `app.run()` in a server (non-Emscripten) environment
- **THEN** a `WebComPyException` SHALL be raised indicating that `run()` is only available in the browser

#### Scenario: Mounting into a non-existent element
- **WHEN** a developer calls `app.run("#nonexistent")` and no element matches
- **THEN** a `WebComPyException` SHALL be raised indicating the mount point was not found

### Requirement: The server entry point shall be a module-level function
Server-side entry points SHALL be module-level functions (`create_asgi_app`, `run_server`) that accept a `WebComPyApp` instance, not methods on the app object. This avoids importing server-only dependencies (starlette, uvicorn) in the browser environment.

#### Scenario: Creating an ASGI app from a WebComPyApp
- **WHEN** a developer calls `create_asgi_app(app, config, dev_mode)` on the server
- **THEN** a Starlette ASGI application SHALL be returned
- **AND** the ASGI app SHALL serve all routes, static files, and app packages

#### Scenario: Starting a dev server with run_server
- **WHEN** a developer calls `run_server(app)` on the server
- **THEN** a uvicorn server SHALL start on the configured port (default 8080)
- **AND** the application SHALL be accessible at the configured base URL
- **AND** hot-reload SHALL be enabled via SSE when run in dev mode

#### Scenario: Starting a dev server via CLI without webcompy_config.py
- **WHEN** a developer runs `python -m webcompy start --dev` and the app module exposes `app = WebComPyApp(..., config=AppConfig(...))`
- **THEN** the CLI SHALL discover the app instance and use `run_server(app)`
- **AND** `webcompy_config.py` SHALL not be required

### Requirement: The SSG entry point shall be a module-level function
Static site generation SHALL use a module-level function (`generate_static_site`) that accepts a `WebComPyApp` instance, not a method on the app object.

#### Scenario: Generating a static site from a WebComPyApp
- **WHEN** a developer calls `generate_static_site(app)` on the server
- **THEN** a `dist/` directory SHALL be created with pre-rendered HTML for each route
- **AND** a bundled Python wheel SHALL be included
- **AND** static files SHALL be copied
- **AND** a `.nojekyll` file SHALL be created

#### Scenario: Generating via CLI without webcompy_config.py
- **WHEN** a developer runs `python -m webcompy generate` and the app module exposes a `WebComPyApp` instance
- **THEN** the CLI SHALL discover the app instance and use `generate_static_site(app)`
- **AND** `webcompy_config.py` SHALL not be required

### Requirement: WebComPyApp shall forward AppDocumentRoot properties
`WebComPyApp` SHALL provide transparent access to frequently used `AppDocumentRoot` properties without requiring `__component__` access.

#### Scenario: Accessing app routes
- **WHEN** a developer accesses `app.routes`
- **THEN** the result SHALL be identical to `app.__component__.routes` (deprecated form)

#### Scenario: Setting the path programmatically
- **WHEN** a developer calls `app.set_path("/users/42")`
- **THEN** the router SHALL navigate to `/users/42`
- **AND** the result SHALL be identical to calling `app.__component__.set_path("/users/42")` (deprecated form)

#### Scenario: Accessing head management
- **WHEN** a developer calls `app.set_title("My Page")` or accesses `app.head`
- **THEN** the behavior SHALL be identical to calling the corresponding method on `app.__component__` (deprecated form)