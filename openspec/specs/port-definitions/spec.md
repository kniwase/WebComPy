## Purpose

Port ABCs provide a typed, injectable abstraction layer for browser and server runtime operations (DOM manipulation, FFI bridging, HTTP fetching, cookie management, and history navigation). They replace direct access to the monolithic `browser` object, enabling testable, swappable implementations via dependency injection.

## Requirements

### Requirement: Port ABC definitions exist
The system SHALL provide abstract base classes for DOM, FFI, fetch, cookie, and history operations in the `webcompy.ports` package. Each ABC SHALL declare abstract methods for its specific concern. `HistoryPort` SHALL extend `SignalBase[str]` to enable reactive path state.

#### Scenario: All ABCs are importable
- **WHEN** a developer imports `webcompy.ports`
- **THEN** all 5 port ABCs (DOMPort, FFIPort, FetchPort, CookiePort, HistoryPort) and DOMNode are accessible

#### Scenario: ABCs cannot be instantiated directly
- **WHEN** a developer attempts to instantiate any port ABC directly
- **THEN** Python raises TypeError due to abstract methods

### Requirement: Browser port implementations exist
The system SHALL provide browser implementations for all 5 ports using `pyscript.context` and `pyscript.ffi`. These SHALL be located in `webcompy.ports._browser`.

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
The system SHALL provide server implementations for all 5 ports. FetchPort SHALL use `httpx`. Other ports SHALL use internal state. These SHALL be located in `webcompy.ports._server`. ServerDOMPort SHALL raise `WebComPyException` on DOM node creation. Server-side port implementations SHALL be excluded from browser wheels via the `_BROWSER_ONLY_EXCLUDE` mechanism.

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
The system SHALL define DI injection keys in `webcompy.ports._keys` for all 5 ports.

#### Scenario: Keys are importable and unique
- **WHEN** all 5 port keys are imported from `webcompy.ports._keys`
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
