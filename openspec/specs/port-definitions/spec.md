## Purpose

Port ABCs provide a typed, injectable abstraction layer for browser and server runtime operations (DOM manipulation, window operations, FFI bridging, HTTP fetching, cookie management, and history navigation). They replace direct access to the monolithic `browser` object, enabling testable, swappable implementations via dependency injection. Ports are organized around distinct browser API surfaces: `DOMPort` for document-level operations, `HostPort` for general window-level operations, and dedicated ports for specific sub-APIs (`CookiePort`, `HistoryPort`, `FetchPort`) or non-web-platform concerns (`FFIPort`).

## Requirements

### Requirement: Port ABC definitions exist
The system SHALL provide abstract base classes for DOM, host (window), FFI, fetch, cookie, and history operations in the `webcompy.ports` package. Each ABC SHALL declare abstract methods for its specific concern. `HistoryPort` SHALL extend `SignalBase[str]` to enable reactive path state.

#### Scenario: All ABCs are importable
- **WHEN** a developer imports `webcompy.ports`
- **THEN** all 6 port ABCs (DOMPort, HostPort, FFIPort, FetchPort, CookiePort, HistoryPort) and DOMNode are accessible

#### Scenario: ABCs cannot be instantiated directly
- **WHEN** a developer attempts to instantiate any port ABC directly
- **THEN** Python raises TypeError due to abstract methods

### Requirement: Browser port implementations exist
The system SHALL provide browser implementations for all 6 ports using `pyscript.context` and `pyscript.ffi`. These SHALL be located in `webcompy.ports._browser`.

#### Scenario: BrowserDOMPort creates real DOM elements
- **WHEN** `BrowserDOMPort.create_element("div")` is called in a PyScript environment
- **THEN** a raw browser `HTMLDivElement` is returned
- **AND** `BrowserDOMPort.create_text_node("hello")` SHALL return a raw browser `Text` node
- **AND** both SHALL satisfy the `DOMNode` Protocol structurally (no nominal inheritance required)

#### Scenario: BrowserFFIPort uses pyscript.ffi
- **WHEN** `BrowserFFIPort.create_proxy(some_func)` is called
- **THEN** `pyscript.ffi.create_proxy(some_func)` is invoked

#### Scenario: BrowserHistoryPort reads from window.location
- **WHEN** a `BrowserHistoryPort` is constructed in a PyScript environment with mode="history"
- **THEN** its `value` property returns the current `window.location.pathname`

### Requirement: Server port implementations exist
The system SHALL provide server implementations for all 6 ports. FetchPort SHALL use `httpx`. Other ports SHALL use internal state. These SHALL be located in `webcompy.ports._server`. ServerDOMPort SHALL raise `WebComPyException` on DOM node creation. Server-side port implementations SHALL be excluded from browser wheels via the `_BROWSER_ONLY_EXCLUDE` mechanism.

#### Scenario: ServerDOMPort rejects DOM creation
- **WHEN** `ServerDOMPort.create_element("div")` or `create_text_node(...)` is called on the server
- **THEN** it SHALL raise `WebComPyException` with a message indicating DOM operations are not available outside the browser

#### Scenario: ServerFetchPort uses httpx
- **WHEN** `ServerFetchPort.fetch("https://example.com/api")` is called
- **THEN** an httpx request is sent and a `Response` object is returned

#### Scenario: ServerHistoryPort stores path internally
- **WHEN** `ServerHistoryPort.navigate("/test")` is called
- **THEN** the port's `value` property returns "/test"

#### Scenario: ServerCookiePort ignores Set-Cookie attributes (current limitation)
- **WHEN** `ServerCookiePort.set(name, value, max_age=3600, secure=True, samesite="Strict")` is called on the server
- **THEN** only the name/value pair is stored in the internal dict
- **AND** the `max_age`, `secure`, `httponly`, `path`, and `samesite` parameters are discarded
- **NOTE**: When embedded API server or RPC functionality is implemented in a future change, cookie attributes SHALL be propagated via `Set-Cookie` response headers. The current internal-state implementation is sufficient for SSR/SSG where cookies are read-only.

### Requirement: DI keys are defined
The system SHALL define DI injection keys in `webcompy.ports._keys` for all 6 ports.

#### Scenario: Keys are importable and unique
- **WHEN** all 6 port keys are imported from `webcompy.ports._keys`
- **THEN** each key is a distinct `InjectKey` instance usable with `inject()` and `provide()`

### Requirement: DOMNode Protocol methods are available
The `DOMNode` Protocol SHALL expose tree manipulation (`appendChild`, `removeChild`, `insertBefore`, `replaceChild`, `remove`), attribute methods (`setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`), event methods (`addEventListener`, `removeEventListener`), content properties (`textContent`, `childNodes` (returns `DOMNodeList`), `parentNode`, `nodeName`, `nodeType`), and WebComPy markers (`__webcompy_node__`, `__webcompy_prerendered_node__`). Any object — raw JS node or `VirtualDOMNode` — that structurally satisfies these members SHALL be accepted as a `DOMNode`.

#### Scenario: Raw JS nodes satisfy DOMNode Protocol
- **WHEN** a raw `document.createElement("div")` value is returned from `BrowserDOMPort.create_element()`
- **THEN** it SHALL satisfy the `DOMNode` Protocol structurally
- **AND** the elements layer SHALL operate on it without `cast` wrappers

#### Scenario: DOMNodeList provides length and indexing
- **WHEN** code accesses `node.childNodes` on a DOMNode
- **THEN** it SHALL return a `DOMNodeList` instance
- **AND** `DOMNodeList` SHALL support `.length` (int) and `[index]` access returning `DOMNode`

### Requirement: Port responsibilities are scoped by browser API surface
Ports SHALL be organized around distinct browser API surfaces rather than arbitrary groupings. `DOMPort` SHALL handle document-level operations (`document.createElement`, `document.querySelector`, `document.title`, `document.addEventListener`). `HostPort` SHALL handle general window-level operations (JS global object access via `window[name]`, `window.setTimeout` for macro-task scheduling). Additional port ABCs SHALL be introduced when a new category of browser API surface is identified, following MDN's classification of browser features. This ensures each port has a clear, narrow responsibility and prevents ports from becoming monolithic catch-all abstractions.

Existing ports already demonstrate this principle:
- `CookiePort` is an independent port for `document.cookie`, separate from `DOMPort`'s broader document operations.
- `HistoryPort` is an independent port for `window.location` and `window.history`, separate from `HostPort`'s general window operations.
- `FetchPort` is an independent port for the global `fetch()` API, which belongs to neither document nor window.
- `FFIPort` is an independent port for the PyScript/Emscripten Python-to-JS bridge — not a web platform API at all, but its own distinct concern.

#### Scenario: Document operations belong to DOMPort
- **WHEN** a framework operation interacts with `document` (element creation, selector queries, title, document event listeners)
- **THEN** it SHALL use `DOMPort`

#### Scenario: Window operations belong to HostPort
- **WHEN** a framework operation interacts with `window` (JS globals, `setTimeout`)
- **THEN** it SHALL use `HostPort`

#### Scenario: Specific document or window sub-APIs get their own ports
- **WHEN** a browser API surface under `document` or `window` has sufficient scope to warrant independent abstraction (e.g., `document.cookie` → `CookiePort`, `window.location` + `window.history` → `HistoryPort`)
- **THEN** a dedicated port SHALL be introduced for that sub-API
- **AND** the general port (`DOMPort` or `HostPort`) SHALL NOT absorb it

#### Scenario: APIs outside document/window get their own ports
- **WHEN** a browser API surface does not belong to `document` or `window` (e.g., `fetch()` → `FetchPort`, `navigator` in the future)
- **THEN** a dedicated port SHALL be introduced for that API surface

#### Scenario: Non-web-platform concerns get their own ports
- **WHEN** a concern is not a web platform API but a runtime bridge or tooling abstraction (e.g., PyScript/Emscripten FFI → `FFIPort`)
- **THEN** it MAY have its own dedicated port

#### Scenario: Scope creep is rejected
- **WHEN** a need arises for a browser API surface that does not fit an existing port's scope
- **THEN** a new port SHALL be introduced rather than extending an existing port
- **AND** the existing port ABCs SHALL NOT be extended with methods outside their scope
