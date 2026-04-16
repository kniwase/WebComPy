# Browser API Abstraction

## Purpose

WebComPy applications need to interact with browser APIs — the DOM, event system, fetch, history, and more. These APIs only exist in the browser environment, but the same Python codebase must also run on the server for static site generation. The browser API abstraction layer solves this by providing a `browser` object that is `None` on the server and a dynamic proxy in the browser, allowing all browser-dependent code to be gated behind a simple `if browser:` check.

## Requirements

### Requirement: The framework shall detect the browser environment at import time
The `ENVIRONMENT` variable SHALL be computed once when the module is imported: `"pyscript"` when running under PyScript (detected by `platform.system() == "Emscripten"`), and `"other"` otherwise.

#### Scenario: Running in the browser via PyScript
- **WHEN** the application runs in PyScript/Emscripten
- **THEN** `ENVIRONMENT` SHALL equal `"pyscript"`
- **AND** `browser` SHALL be a proxy object providing access to browser APIs

#### Scenario: Running on a standard Python server
- **WHEN** the application runs on a standard Python interpreter
- **THEN** `ENVIRONMENT` SHALL equal `"other"`
- **AND** `browser` SHALL be `None`

### Requirement: Browser API access shall be gated with explicit checks
All code that uses browser APIs SHALL check `if browser:` before accessing browser-dependent functionality. Code that cannot function without browser APIs SHALL raise a clear error when `browser` is `None`.

#### Scenario: Creating a DOM element
- **WHEN** the framework attempts to create a DOM element
- **AND** `browser` is `None` (server environment)
- **THEN** `WebComPyException` with message "Not in Browser environment." SHALL be raised

### Requirement: The browser proxy shall provide access to all window APIs
When running in the browser, the `browser` object SHALL provide access to `document`, `window`, `pyscript`, `pyodide`, `fetch`, `FormData`, and all other properties of the JavaScript `window` object.

#### Scenario: Accessing the document object
- **WHEN** `browser.document` is accessed in the browser
- **THEN** the actual `window.document` SHALL be returned
- **AND** developers SHALL be able to call DOM methods like `createElement`, `getElementById`, etc.

### Requirement: JavaScript proxy objects shall be created and destroyed properly
Objects that bridge Python and JavaScript (such as event handlers) SHALL be created via `pyscript.ffi.create_proxy()` and SHALL be destroyed when no longer needed to prevent memory leaks.

#### Scenario: Registering an event handler
- **WHEN** a DOM event handler is registered
- **THEN** the handler SHALL be wrapped with `pyscript.ffi.create_proxy()`
- **AND** when the element is removed, `destroy()` SHALL be called on the proxy

#### Scenario: Cleanup on element removal
- **WHEN** an element with registered event handlers is removed from the DOM
- **THEN** `removeEventListener` SHALL be called for each handler
- **AND** each proxy SHALL be `destroy()`ed to release the JavaScript reference