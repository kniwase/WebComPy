# Browser API Abstraction (delta)

## MODIFIED Requirements

### Requirement: The framework shall detect the browser environment at import time

The `ENVIRONMENT` variable SHALL be computed once when the module is imported: `"pyscript"` when running under PyScript (detected by `platform.system() == "Emscripten"`), and `"other"` otherwise. When running in the browser, the `browser` object SHALL remain available as a deprecated shim; framework code SHALL use port Protocol interfaces with DI-injectable implementations instead.

#### Scenario: Running in the browser via PyScript
- **WHEN** the application runs in PyScript/Emscripten
- **THEN** `ENVIRONMENT` SHALL equal `"pyscript"`
- **AND** port implementations (`BrowserDOMPort`, `BrowserFFIPort`, etc.) SHALL be provided into `app.di_scope`
- **AND** the deprecated `browser` object SHALL still be accessible

#### Scenario: Running on a standard Python server
- **WHEN** the application runs on a standard Python interpreter
- **THEN** `ENVIRONMENT` SHALL equal `"other"`
- **AND** port implementations (`ServerDOMPort`, `ServerFFIPort`, etc.) SHALL be provided into `app.di_scope`
- **AND** the deprecated `browser` object SHALL be `None`

### Requirement: Browser API access shall be gated with injectable port implementations

Framework code SHALL access browser APIs through `inject(PORT_KEY)` calls to typed port Protocol interfaces, not through direct `if browser:` checks on the monolithic `browser` object. Port implementations SHALL be selected at bootstrap based on environment, enabling the same code path to work with browser JS objects, server-side mock objects, or test spy objects. Code that cannot function without browser APIs SHALL raise a clear error when the port implementation does not support the operation.

#### Scenario: Creating a DOM element
- **WHEN** the framework attempts to create a DOM element
- **AND** the injected `DOMPort` implementation is `ServerDOMPort` (phase 1)
- **THEN** `WebComPyException` SHALL be raised with a message indicating DOM operations are not available outside the browser

#### Scenario: Using FFIPort on server
- **WHEN** framework code calls `ffi.create_proxy(handler)` on the server
- **THEN** `ServerFFIPort` SHALL return `handler` directly without proxy wrapping
- **AND** no exception SHALL be raised

### Requirement: The browser proxy shall provide access to all window APIs

When running in the browser, the `browser` object SHALL provide access to `document`, `window`, `pyscript`, `pyodide`, `fetch`, `FormData`, and all other properties of the JavaScript `window` object. This object is **DEPRECATED** — new code SHALL use port Protocol interfaces instead.

#### Scenario: Accessing the document object through ports (recommended)
- **WHEN** framework code calls `inject(DOM_PORT_KEY).create_element("div")` in the browser
- **THEN** `BrowserDOMPort` SHALL delegate to `pyscript.context.document.createElement("div")`
- **AND** return a `BrowserDOMNode` wrapping the JS element

#### Scenario: Accessing the document object through deprecated browser object
- **WHEN** `browser.document` is accessed in the browser
- **THEN** a `DeprecationWarning` SHALL be emitted
- **AND** the actual `window.document` SHALL be returned as before

### Requirement: JavaScript proxy objects shall be created and destroyed through FFIPort

Objects that bridge Python and JavaScript (such as event handlers) SHALL be created via `inject(FFI_PORT_KEY).create_proxy()` and SHALL be destroyed via `inject(FFI_PORT_KEY).destroy_proxy()` when no longer needed. The browser implementation SHALL delegate to `pyscript.ffi.create_proxy()` and `.destroy()` respectively. The server implementation SHALL return the function as-is and make `destroy_proxy` a no-op.

#### Scenario: Registering an event handler in the browser
- **WHEN** a DOM event handler is registered
- **THEN** the handler SHALL be wrapped with `BrowserFFIPort.create_proxy()` which delegates to `pyscript.ffi.create_proxy()`
- **AND** when the element is removed, `BrowserFFIPort.destroy_proxy()` SHALL call `destroy()` on the proxy

#### Scenario: Registering an event handler on the server
- **WHEN** a DOM event handler is registered on the server
- **THEN** `ServerFFIPort.create_proxy(handler)` SHALL return `handler` directly
- **AND** `ServerFFIPort.destroy_proxy()` SHALL be a no-op

#### Scenario: Cleanup on element removal
- **WHEN** an element with registered event handlers is removed from the DOM
- **THEN** `removeEventListener` SHALL be called for each handler
- **AND** each proxy SHALL be released via the injected FFIPort

## ADDED Requirements

### Requirement: HTTP requests shall go through FetchPort

All HTTP requests initiated by the framework SHALL use `inject(FETCH_PORT_KEY)` to obtain a port implementation. The browser implementation SHALL delegate to `pyscript.fetch`; the server implementation SHALL use `httpx`.

#### Scenario: HTTP GET in browser
- **WHEN** `BrowserFetchPort.request("GET", url)` is called
- **THEN** it SHALL delegate to `pyscript.fetch(url, method="GET")`
- **AND** return a `Response` object with the standard properties

#### Scenario: HTTP POST with JSON body in browser
- **WHEN** `BrowserFetchPort.request("POST", url, json=data)` is called
- **THEN** it SHALL set `Content-Type: application/json` and serialize `data` as the body
- **AND** delegate to `pyscript.fetch`

#### Scenario: HTTP GET on server
- **WHEN** `ServerFetchPort.request("GET", url)` is called
- **THEN** it SHALL perform the request using `httpx.AsyncClient.get(url)`
- **AND** return a `Response` object matching the same interface

### Requirement: Macro-task scheduling shall be abstracted through DOMPort

Code that needs to defer execution to a subsequent macro-task (currently via `setTimeout(fn, 0)`) SHALL call `inject(DOM_PORT_KEY).schedule_macro_task(callback)`. The browser implementation SHALL use `pyscript.context.window.setTimeout(callback, 0)`. The server implementation SHALL execute the callback synchronously (phase 1).

#### Scenario: Effect batching in browser
- **WHEN** `DOMPort.schedule_macro_task(_flush_pending_effects)` is called in the browser
- **THEN** effects SHALL be flushed in a subsequent macro-task via `setTimeout(..., 0)`

#### Scenario: Effect batching on server
- **WHEN** `DOMPort.schedule_macro_task(_flush_pending_effects)` is called on the server
- **THEN** effects SHALL be flushed synchronously
