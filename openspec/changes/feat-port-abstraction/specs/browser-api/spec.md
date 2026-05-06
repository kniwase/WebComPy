# Browser API Abstraction (delta)

## REMOVED Requirements

### Requirement: The browser proxy shall provide access to all window APIs

The `browser` object and `webcompy/_browser/` module are **REMOVED**. All browser API access now goes through typed port Protocol interfaces with DI-injectable implementations. The `from webcompy import browser` import path no longer exists.

## MODIFIED Requirements

### Requirement: The framework shall detect the browser environment at import time

The `ENVIRONMENT` variable SHALL be computed once when the module is imported: `"pyscript"` when running under PyScript (detected by `platform.system() == "Emscripten"`), and `"other"` otherwise. Framework code SHALL use port Protocol interfaces with DI-injectable implementations.

#### Scenario: Running in the browser via PyScript
- **WHEN** the application runs in PyScript/Emscripten
- **THEN** `ENVIRONMENT` SHALL equal `"pyscript"`
- **AND** port implementations (`BrowserDOMPort`, `BrowserFFIPort`, `BrowserFetchPort`, `BrowserCookiePort`) SHALL be provided into `app.di_scope`
- **AND** router-internal `BrowserHistoryPort` SHALL be provided into `app.di_scope`

#### Scenario: Running on a standard Python server
- **WHEN** the application runs on a standard Python interpreter
- **THEN** `ENVIRONMENT` SHALL equal `"other"`
- **AND** port implementations (`ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerCookiePort`) SHALL be provided into `app.di_scope`
- **AND** router-internal `ServerHistoryPort` SHALL be provided into `app.di_scope`

### Requirement: Browser API access shall be gated with injectable port implementations

Framework code SHALL access browser APIs through `inject(PORT_KEY)` calls to typed port Protocol interfaces, not through direct `if browser:` checks or direct `pyscript.context.window` access. Port implementations SHALL be selected at bootstrap based on environment, enabling the same code path to work with browser JS objects, server-side mock objects, or test spy objects.

#### Scenario: Creating a DOM element
- **WHEN** the framework attempts to create a DOM element
- **AND** the injected `DOMPort` implementation is `ServerDOMPort` (phase 1)
- **THEN** `WebComPyException` SHALL be raised with a message indicating DOM operations are not available outside the browser

#### Scenario: Using FFIPort on server
- **WHEN** framework code calls `ffi.create_proxy(handler)` on the server
- **THEN** `ServerFFIPort` SHALL return `handler` directly without proxy wrapping
- **AND** no exception SHALL be raised

#### Scenario: Navigating via HistoryPort in browser
- **WHEN** `RouterLink._on_click` triggers navigation
- **THEN** it SHALL call `inject(HISTORY_PORT_KEY).navigate(href, state, mode)`
- **AND** the browser implementation SHALL call `pyscript.context.window.history.pushState(state, None, href)`

#### Scenario: Reading history path via HistoryPort on server
- **WHEN** SSG requires the current path
- **THEN** `inject(HISTORY_PORT_KEY).current_path(mode)` SHALL return the internally stored path
- **AND** no browser API SHALL be accessed

### Requirement: JavaScript proxy objects shall be created and destroyed through FFIPort

Objects that bridge Python and JavaScript (such as event handlers) SHALL be created via `inject(FFI_PORT_KEY).create_proxy()` and SHALL be destroyed via `inject(FFI_PORT_KEY).destroy_proxy()` when no longer needed.

#### Scenario: Registering an event handler in the browser
- **WHEN** a DOM event handler is registered
- **THEN** the handler SHALL be wrapped via `inject(FFI_PORT_KEY).create_proxy()`
- **AND** when the element is removed, the proxy SHALL be released via `inject(FFI_PORT_KEY).destroy_proxy()`

## ADDED Requirements

### Requirement: Cookie access shall go through CookiePort

All cookie read/write/delete operations SHALL use `inject(COOKIE_PORT_KEY)` to obtain a port implementation. The browser implementation SHALL delegate to `document.cookie`; the server implementation SHALL parse request `Cookie` headers and accumulate `Set-Cookie` response headers.

#### Scenario: Reading a cookie in browser
- **WHEN** `BrowserCookiePort.get("session")` is called
- **THEN** it SHALL parse `document.cookie` and return the matching value
- **AND** return `None` if not found

#### Scenario: Setting a cookie on server
- **WHEN** `ServerCookiePort.set("theme", "dark", path="/", httponly=True)` is called
- **THEN** it SHALL accumulate a `Set-Cookie` response header with the specified attributes

### Requirement: HTTP requests shall go through FetchPort

All HTTP requests initiated by the framework SHALL use `inject(FETCH_PORT_KEY)` to obtain a port implementation. The browser implementation SHALL delegate to `pyscript.fetch`; the server implementation SHALL use `httpx`.

#### Scenario: HTTP GET in browser
- **WHEN** `BrowserFetchPort.request("GET", url)` is called
- **THEN** it SHALL delegate to `pyscript.fetch(url, method="GET")`
- **AND** return a `Response` object

#### Scenario: HTTP GET on server
- **WHEN** `ServerFetchPort.request("GET", url)` is called
- **THEN** it SHALL perform the request using `httpx.AsyncClient`
- **AND** return a `Response` object matching the same interface

### Requirement: Macro-task scheduling shall be abstracted through DOMPort

Code that needs to defer execution to a subsequent macro-task SHALL call `inject(DOM_PORT_KEY).schedule_macro_task(callback)`. The browser implementation SHALL use `pyscript.context.window.setTimeout(callback, 0)`. The server implementation SHALL execute the callback synchronously (phase 1).

#### Scenario: Effect batching in browser
- **WHEN** `DOMPort.schedule_macro_task(_flush_pending_effects)` is called in the browser
- **THEN** effects SHALL be flushed in a subsequent macro-task via `setTimeout(..., 0)`

#### Scenario: Effect batching on server
- **WHEN** `DOMPort.schedule_macro_task(_flush_pending_effects)` is called on the server
- **THEN** effects SHALL be flushed synchronously
