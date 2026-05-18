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
All code that uses browser APIs SHALL check `if browser:` or `ENVIRONMENT == "pyscript"` before accessing browser-dependent functionality. Code that cannot function without browser APIs SHALL raise a clear error when `browser` is `None` or `ENVIRONMENT != "pyscript"`.

#### Scenario: Creating a DOM element
- **WHEN** the framework attempts to create a DOM element
- **AND** `browser` is `None` (server environment)
- **THEN** `WebComPyException` with message "Not in Browser environment." SHALL be raised

### Requirement: Element system accesses DOMPort
The elements package SHALL obtain DOM port references through `inject(DOM_PORT_KEY)` from the DI system rather than importing `browser` directly. All existing `if browser:` guards SHALL be replaced with equivalent `if ENVIRONMENT == "pyscript":` checks.

#### Scenario: Element creates DOM element via port
- **WHEN** `ElementBase._create_node()` needs to create a DOM element
- **THEN** it SHALL call `inject(DOM_PORT_KEY).create_element(self._tag_name)` when `ENVIRONMENT == "pyscript"`
- **AND** raise `WebComPyException` otherwise

#### Scenario: Event handler creates proxy via FFIPort
- **WHEN** `_generate_event_handler()` creates an event handler
- **THEN** it SHALL call `inject(FFI_PORT_KEY).create_proxy(handler)` when `ENVIRONMENT == "pyscript"`
- **AND** return the raw Python handler otherwise

#### Scenario: SwitchElement schedules macro task via port
- **WHEN** `SwitchElement._refresh()` has deferred callbacks
- **THEN** it SHALL call `inject(HOST_PORT_KEY).schedule_macro_task(callback)` when `ENVIRONMENT == "pyscript"`

#### Scenario: RepeatElement uses ENVIRONMENT for runtime branching
- **WHEN** `RepeatElement._on_set_parent()` or `_update_dom_range()` runs
- **THEN** it SHALL use `ENVIRONMENT == "pyscript"` instead of `browser` truthiness checks
- **AND** behavior SHALL be identical to the pre-port implementation

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

### Requirement: AJAX accesses fetch via port
The `webcompy.ajax` module SHALL obtain HTTP functionality through `inject(FETCH_PORT_KEY)` rather than `browser.pyscript.fetch`, except for FormData requests which SHALL fall back to raw `browser` directly until a FormData-capable port exists.

#### Scenario: Ajax uses injected FetchPort
- **WHEN** `webcompy.ajax._fetch` performs an HTTP request with JSON or string body
- **THEN** it SHALL call `inject(FETCH_PORT_KEY).fetch(...)` instead of `browser.pyscript.fetch(...)`

#### Scenario: Ajax uses raw browser for FormData
- **WHEN** `webcompy.ajax._fetch` performs an HTTP request with FormData body
- **THEN** it SHALL use raw `browser.fetch` directly with `browser.FormData`

### Requirement: Logging uses pyscript.context directly
The `webcompy.logging` module SHALL use `pyscript.context.window.console` directly (with its full method set: debug, info, warn, error) when in PyScript environment, without port abstraction.

#### Scenario: Logging outputs to browser console
- **WHEN** any logging level (debug, info, warn, error) is called in PyScript environment
- **THEN** it SHALL output via the corresponding method on `pyscript.context.window.console`

### Requirement: Effect scheduling uses HostPort.schedule_macro_task
The signal effect system SHALL schedule deferred callbacks through `inject(HOST_PORT_KEY).schedule_macro_task()`.

#### Scenario: Effects scheduled via port
- **WHEN** `_schedule_effect` runs in PyScript environment
- **THEN** it SHALL use `inject(HOST_PORT_KEY).schedule_macro_task(_flush_pending_effects)`
- **AND** fall back to synchronous execution if injection fails

### Requirement: HostPort provides window-level operations
A `HostPort` SHALL provide the `schedule_macro_task` and `create_js_global_getter` methods for window-level operations, separate from `DOMPort`'s document-level operations.

#### Scenario: schedule_macro_task deferred via HostPort
- **WHEN** framework code calls `host_port.schedule_macro_task(callback)`
- **THEN** in the browser, the callback SHALL be deferred via `window.setTimeout(callback, 0)`
- **AND** in the server, the call SHALL be a no-op

#### Scenario: create_js_global_getter resolves window globals
- **WHEN** `create_js_global_getter("hljs")` is called in the browser
- **THEN** the returned zero-arg function SHALL resolve `hljs` from the window object via `getattr(window, "hljs", None)`
- **AND** if `wrapper` is provided, the wrapper function SHALL always be called — receiving the resolved global (or `None` if missing)
- **AND** if the global is missing and no `wrapper` is provided, the result SHALL be `None` (or `default`, if provided)

#### Scenario: create_js_global_getter returns default on server
- **WHEN** `create_js_global_getter("hljs")` is called on the server (SSG)
- **THEN** the returned zero-arg function SHALL return `None` (or `default`, if provided)
- **AND** if `wrapper` is provided, it SHALL be called with `None` (the global is always missing on the server)

#### Scenario: DOMPort no longer carries schedule_macro_task
- **WHEN** code inspects `DOMPort` ABC
- **THEN** `schedule_macro_task` SHALL NOT be present
