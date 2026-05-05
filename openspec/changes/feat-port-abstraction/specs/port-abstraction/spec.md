# Port Abstraction

## Purpose

WebComPy accesses browser APIs through typed port Protocol interfaces injected via the dependency injection system. Each port covers a specific capability domain — DOM manipulation, FFI bridging, HTTP requests, history navigation — with browser and server implementations selected at bootstrap time. This replaces the monolithic `browser` object and enables unit testing of all browser-dependent code through mock port injection.

## ADDED Requirements

### Requirement: Ports shall be defined as Protocol interfaces with explicit method signatures

Each port SHALL be a Python Protocol class declaring the exact methods and type signatures that consumers depend on. Protocol files SHALL be placed in `webcompy/ports/` for public ports and within their owning package for internal ports.

#### Scenario: DOMPort Protocol definition
- **WHEN** `webcompy/ports/_dom.py` is imported
- **THEN** it SHALL export a `DOMPort` Protocol with methods `create_element`, `create_text_node`, `query_selector`, `get_element_by_id`, `set_title`, and `schedule_macro_task`
- **AND** it SHALL export a `DOMNode` Protocol with methods `appendChild`, `insertBefore`, `replaceChild`, `removeChild`, `remove`, `setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`, `addEventListener`, `removeEventListener`, `textContent` (property), `nodeName` (property), `nodeType` (property), and `childNodes` (property)
- **AND** `DOMNode` SHALL declare `__webcompy_node__: bool`

#### Scenario: FFIPort Protocol definition
- **WHEN** `webcompy/ports/_ffi.py` is imported
- **THEN** it SHALL export an `FFIPort` Protocol with methods `create_proxy`, `destroy_proxy`, `is_none`, `to_js`, and `assign`

#### Scenario: FetchPort Protocol definition
- **WHEN** `webcompy/ports/_fetch.py` is imported
- **THEN** it SHALL export a `FetchPort` Protocol with an async `request` method accepting `method`, `url`, `headers`, `query_params`, `json`, `body_data`, `form_data`, and `form_element` parameters

### Requirement: Port implementations shall be selected by environment at bootstrap time

`WebComPyApp` SHALL instantiate the appropriate port implementation for each port based on the current environment and provide them into `app.di_scope`. Browser implementations SHALL be used when `ENVIRONMENT == "pyscript"`; server implementations SHALL be used when `ENVIRONMENT == "other"`.

#### Scenario: Ports provided during browser bootstrap
- **WHEN** `WebComPyApp` is created and `ENVIRONMENT == "pyscript"`
- **THEN** `BrowserDOMPort`, `BrowserFFIPort`, and `BrowserFetchPort` instances SHALL be provided into `app.di_scope` using `DOM_PORT_KEY`, `FFI_PORT_KEY`, and `FETCH_PORT_KEY`
- **AND** all ports SHALL be available via `inject()` during rendering

#### Scenario: Ports provided during server bootstrap
- **WHEN** `WebComPyApp` is created and `ENVIRONMENT == "other"`
- **THEN** `ServerDOMPort`, `ServerFFIPort`, and `ServerFetchPort` instances SHALL be provided into `app.di_scope`
- **AND** the DI scope SHALL be entered as a context manager

### Requirement: Browser port implementations shall use pyscript.context and pyscript.ffi

Browser port implementations SHALL access browser APIs through `pyscript.context.document`, `pyscript.context.window`, and `pyscript.ffi` rather than directly importing the `js` module.

#### Scenario: BrowserDOMPort accesses document
- **WHEN** `BrowserDOMPort.create_element("div")` is called in the browser
- **THEN** it SHALL delegate to `pyscript.context.document.createElement("div")`
- **AND** return a `BrowserDOMNode` wrapping the JS element

#### Scenario: BrowserFFIPort creates a proxy
- **WHEN** `BrowserFFIPort.create_proxy(handler)` is called in the browser
- **THEN** it SHALL delegate to `pyscript.ffi.create_proxy(handler)`
- **AND** return the resulting proxy object

#### Scenario: BrowserFetchPort performs a request
- **WHEN** `BrowserFetchPort.request("GET", url, ...)` is called in the browser
- **THEN** it SHALL delegate to `pyscript.fetch(url, ...)`
- **AND** return a `Response` object with `.text`, `.json()`, `.headers`, `.status_code`, `.ok`, and `.raise_for_status()`

### Requirement: Server port implementations shall provide equivalent behavior

Server port implementations SHALL provide the same method signatures and return types as browser implementations for all non-DOM operations. ServerDOMPort SHALL raise descriptive errors for DOM node creation during phase 1, indicating that only HTML string rendering is available.

#### Scenario: ServerFFIPort returns functions as-is
- **WHEN** `ServerFFIPort.create_proxy(handler)` is called on the server
- **THEN** it SHALL return `handler` directly without any proxy wrapping
- **AND** `ServerFFIPort.destroy_proxy(proxy)` SHALL be a no-op

#### Scenario: ServerFetchPort uses httpx
- **WHEN** `ServerFetchPort.request("GET", url, ...)` is called on the server
- **THEN** it SHALL perform the request using `httpx.AsyncClient`
- **AND** return a `Response` object matching the same interface

#### Scenario: ServerDOMPort rejects DOM creation in phase 1
- **WHEN** `ServerDOMPort.create_element("div")` is called on the server in phase 1
- **THEN** it SHALL raise `WebComPyException` with a message indicating DOM operations are not available outside the browser

### Requirement: History port shall be internal to the router module

`HistoryPort` SHALL be defined within `webcompy/router/` as an internal abstraction, not in the public `webcompy/ports/` package. It SHALL provide methods `current_path`, `current_search`, `navigate`, `on_popstate`, `off_popstate`, and `state` (property). The browser implementation SHALL use `pyscript.context.window.history` and `pyscript.context.window.location`.

#### Scenario: HistoryPort provides current path in browser
- **WHEN** `BrowserHistoryPort.current_path` is accessed
- **THEN** it SHALL return the path from `pyscript.context.window.location.pathname` (history mode) or `pyscript.context.window.location.hash` (hash mode)

#### Scenario: HistoryPort navigates in browser
- **WHEN** `BrowserHistoryPort.navigate("/new-path", state)` is called
- **THEN** it SHALL call `pyscript.context.window.history.pushState(state, None, "/new-path")`

#### Scenario: ServerHistoryPort stores path directly
- **WHEN** `ServerHistoryPort.navigate("/new-path", state)` is called on the server
- **THEN** it SHALL store the path and state internally
- **AND** `current_path` SHALL return the stored path

### Requirement: DOMNode Protocol shall have explicit method declarations

`DOMNode` SHALL be a Protocol with explicit method signatures rather than `__getattr__`/`__setattr__` catch-all patterns. This enables dual-environment implementation — `BrowserDOMNode` wrapping a JS DOM node and `VirtualDOMNode` managing an in-memory tree — that satisfy the same Protocol.

#### Scenario: Node tree operations via Protocol
- **WHEN** framework code calls `parent.appendChild(child)` on a `DOMNode`
- **THEN** the call SHALL work identically whether `parent` is a `BrowserDOMNode` or `VirtualDOMNode`
- **AND** no runtime `browser` environment check SHALL be required at the call site

#### Scenario: Attribute operations via Protocol
- **WHEN** framework code calls `node.setAttribute("id", "foo")` on a `DOMNode`
- **THEN** the call SHALL work identically across all DOMNode implementations

### Requirement: Framework code shall access ports via inject() or constructor injection

All framework code that currently accesses browser APIs SHALL obtain port references through `inject(PORT_KEY)` from the DI system or through constructor parameter injection, rather than importing `browser` directly.

#### Scenario: Element system accesses DOMPort
- **WHEN** `ElementBase._create_node()` needs to create a DOM element
- **THEN** it SHALL call `inject(DOM_PORT_KEY).create_element(self._tag_name)`
- **AND** not check `if browser:` before the operation

#### Scenario: Signal effect schedules via port
- **WHEN** `_schedule_effect()` needs to defer effect execution
- **THEN** it SHALL call `inject(DOM_PORT_KEY).schedule_macro_task(_flush_pending_effects)`
- **AND** on the server, the callback SHALL execute synchronously

### Requirement: The browser object shall be deprecated but remain accessible

The existing `browser` object SHALL remain accessible via `from webcompy import browser` and `from webcompy._browser import browser` during a deprecation period. Accessing it SHALL emit a `DeprecationWarning` directing users to port APIs. Framework-internal code SHALL NOT import `browser` directly after migration.

#### Scenario: Deprecated browser access
- **WHEN** application code accesses `from webcompy import browser`
- **THEN** a `DeprecationWarning` SHALL be emitted
- **AND** the `browser` object SHALL still function as before
