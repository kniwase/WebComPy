# Port Abstraction

## Purpose

WebComPy accesses browser APIs through typed port Protocol interfaces injected via the dependency injection system. Each port covers a specific capability domain — DOM manipulation, FFI bridging, HTTP requests, history navigation, cookie management — with browser and server implementations selected at bootstrap time. This replaces the monolithic `browser` object and enables unit testing of all browser-dependent code through mock port injection.

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

#### Scenario: CookiePort Protocol definition
- **WHEN** `webcompy/ports/_cookie.py` is imported
- **THEN** it SHALL export a `CookiePort` Protocol with methods `get(name) -> str | None`, `set(name, value, *, max_age=None, path="/", secure=False, httponly=False, samesite=None)`, `delete(name, path="/")`, and `get_all() -> dict[str, str]`

### Requirement: Port implementations shall be selected by environment at bootstrap time

`WebComPyApp` SHALL instantiate the appropriate port implementation for each port based on the current environment and provide them into `app.di_scope`. Browser implementations SHALL be used when `ENVIRONMENT == "pyscript"`; server implementations SHALL be used when `ENVIRONMENT == "other"`.

#### Scenario: Ports provided during browser bootstrap
- **WHEN** `WebComPyApp` is created and `ENVIRONMENT == "pyscript"`
- **THEN** `BrowserDOMPort`, `BrowserFFIPort`, `BrowserFetchPort`, `BrowserCookiePort`, and `BrowserHistoryPort` instances SHALL be provided into `app.di_scope`
- **AND** all ports SHALL be available via `inject()` during rendering

#### Scenario: Ports provided during server bootstrap
- **WHEN** `WebComPyApp` is created and `ENVIRONMENT == "other"`
- **THEN** `ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerCookiePort`, and `ServerHistoryPort` instances SHALL be provided into `app.di_scope`
- **AND** the DI scope SHALL be entered as a context manager

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

### Requirement: HistoryPort shall be actively used by Location and RouterLink

`HistoryPort` SHALL be the single abstraction for all history and location operations. `Location` SHALL delegate history reads and popstate monitoring to `HistoryPort`. `RouterLink` SHALL delegate navigation to `HistoryPort`. Both `Location` and `RouterLink` SHALL obtain `HistoryPort` via `inject(HISTORY_PORT_KEY)`.

#### Scenario: Location reads path via HistoryPort
- **WHEN** `Location._refresh_path()` is called
- **THEN** it SHALL read `current_path` from the injected `HistoryPort`
- **AND** `current_path` SHALL return `pathname` in history mode and `hash` in hash mode

#### Scenario: RouterLink navigates via HistoryPort
- **WHEN** `RouterLink._on_click()` is triggered in the browser
- **THEN** it SHALL call `inject(HISTORY_PORT_KEY).navigate(href, state)`

#### Scenario: HistoryPort handles popstate events
- **WHEN** `Location.__init__` is called in the browser
- **THEN** it SHALL register a popstate listener via `inject(HISTORY_PORT_KEY).on_popstate(callback)`
- **AND** `Location.destroy()` SHALL call `HistoryPort.off_popstate(handle)`

### Requirement: Router shall receive Location via constructor injection

`Router` SHALL accept a `Location` instance as a constructor parameter rather than creating one internally. This allows `Location` to be constructed after the DI scope is active (with all ports provided), and enables testing with mock `Location` implementations.

#### Scenario: Router receives Location externally
- **WHEN** `Router` is instantiated
- **THEN** it SHALL accept `location: Location` as a required constructor parameter
- **AND** SHALL not create a `Location` instance internally

#### Scenario: Bootstrap creates Location with active DI scope
- **WHEN** `WebComPyApp.__init__` bootstraps the application
- **THEN** ports SHALL be provided into `app.di_scope` first
- **AND** `Location` SHALL be constructed within the active DI scope
- **AND** `Router` SHALL receive the constructed `Location`

### Requirement: CookiePort shall provide cross-environment cookie access

`CookiePort` SHALL provide a uniform API for reading, writing, and deleting cookies across browser and server environments. The browser implementation SHALL delegate to `document.cookie`. The server implementation SHALL parse request `Cookie` headers and accumulate `Set-Cookie` headers for response.

#### Scenario: Reading a cookie in the browser
- **WHEN** `BrowserCookiePort.get("session_id")` is called
- **THEN** it SHALL parse `document.cookie` and return the value for the matching key
- **AND** return `None` if the key is not found

#### Scenario: Setting a cookie in the browser
- **WHEN** `BrowserCookiePort.set("theme", "dark", path="/", max_age=3600)` is called
- **THEN** it SHALL write to `document.cookie` with the appropriate attributes

#### Scenario: Reading a cookie on the server
- **WHEN** `ServerCookiePort.get("session_id")` is called
- **THEN** it SHALL parse the `Cookie` request header and return the value
- **AND** return `None` if the key is not found

#### Scenario: Setting a cookie on the server
- **WHEN** `ServerCookiePort.set("theme", "dark", path="/", max_age=3600)` is called
- **THEN** it SHALL accumulate a `Set-Cookie` header for the response
- **AND** the header SHALL include the specified attributes

### Requirement: Browser port implementations shall use pyscript.context and pyscript.ffi

Browser port implementations SHALL access browser APIs through `pyscript.context.document`, `pyscript.context.window`, and `pyscript.ffi` rather than directly importing the `js` module.

#### Scenario: BrowserDOMPort accesses document
- **WHEN** `BrowserDOMPort.create_element("div")` is called in the browser
- **THEN** it SHALL delegate to `pyscript.context.document.createElement("div")`
- **AND** return a `BrowserDOMNode` wrapping the JS element

### Requirement: Server port implementations shall provide equivalent behavior

Server port implementations SHALL provide the same method signatures and return types as browser implementations for all non-DOM operations. ServerDOMPort SHALL raise descriptive errors for DOM node creation during phase 1.

#### Scenario: ServerFetchPort uses httpx
- **WHEN** `ServerFetchPort.request("GET", url, ...)` is called on the server
- **THEN** it SHALL perform the request using `httpx.AsyncClient`
- **AND** return a `Response` object matching the same interface

#### Scenario: ServerDOMPort rejects DOM creation in phase 1
- **WHEN** `ServerDOMPort.create_element("div")` is called on the server in phase 1
- **THEN** it SHALL raise `WebComPyException` with a message indicating DOM operations are not available outside the browser

### Requirement: DOMNode Protocol shall have explicit method declarations

`DOMNode` SHALL be a Protocol with explicit method signatures rather than `__getattr__`/`__setattr__` catch-all patterns.

#### Scenario: Node tree operations via Protocol
- **WHEN** framework code calls `parent.appendChild(child)` on a `DOMNode`
- **THEN** the call SHALL work identically whether `parent` is a `BrowserDOMNode` or `VirtualDOMNode`
- **AND** no runtime environment check SHALL be required at the call site
