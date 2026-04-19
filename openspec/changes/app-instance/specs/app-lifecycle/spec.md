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

### Requirement: The application shall provide a development server entry point via app.serve()
In the server environment, `app.serve(config)` SHALL start a Starlette+uvicorn development server that serves the application with hot-reload support.

#### Scenario: Starting a dev server with defaults
- **WHEN** a developer calls `app.serve(dev=True)` on the server
- **THEN** a uvicorn server SHALL start on the configured port (default 8080)
- **AND** the application SHALL be accessible at the configured base URL
- **AND** hot-reload SHALL be enabled via SSE

#### Scenario: Starting a server with custom config
- **WHEN** a developer calls `app.serve(config=ServerConfig(port=9000, dev=True))`
- **THEN** the server SHALL start on port 9000
- **AND** all application routes SHALL be served

#### Scenario: Calling serve() in the browser environment
- **WHEN** a developer calls `app.serve()` in the browser (Emscripten) environment
- **THEN** a `WebComPyException` SHALL be raised indicating that `serve()` is not available in the browser

### Requirement: The application shall expose an ASGI application via app.asgi_app
`app.asgi_app` SHALL return a Starlette ASGI application that can be mounted into other ASGI frameworks or passed directly to ASGI servers.

#### Scenario: Mounting a WebComPy app into an existing Starlette app
- **WHEN** a developer writes `starlette_app = Starlette(routes=[Mount("/app", app=my_webcompy_app.asgi_app)])`
- **THEN** the WebComPy application SHALL be served under the `/app` path
- **AND** all routes, static files, and app packages SHALL be accessible

#### Scenario: Passing asgi_app to uvicorn directly
- **WHEN** a developer writes `uvicorn.run(my_app.asgi_app, host="0.0.0.0", port=8080)`
- **THEN** the server SHALL start and serve the application

#### Scenario: Lazy construction of ASGI app
- **WHEN** a developer accesses `app.asgi_app` multiple times
- **THEN** the ASGI application SHALL be constructed on first access and cached
- **AND** subsequent accesses SHALL return the same ASGI application instance

### Requirement: The application shall provide a static site generation entry point via app.generate()
In the server environment, `app.generate(config)` SHALL produce a complete static site in the configured output directory.

#### Scenario: Generating a static site with defaults
- **WHEN** a developer calls `app.generate()` on the server
- **THEN** a `dist/` directory SHALL be created with pre-rendered HTML for each route
- **AND** a bundled Python wheel SHALL be included
- **AND** static files SHALL be copied
- **AND** a `.nojekyll` file SHALL be created

#### Scenario: Generating with custom config
- **WHEN** a developer calls `app.generate(config=GenerateConfig(dist="docs", cname="example.com"))`
- **THEN** files SHALL be written to the `docs` directory
- **AND** a `CNAME` file SHALL be created with `example.com`

#### Scenario: Calling generate() in the browser environment
- **WHEN** a developer calls `app.generate()` in the browser (Emscripten) environment
- **THEN** a `WebComPyException` SHALL be raised indicating that `generate()` is not available in the browser

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