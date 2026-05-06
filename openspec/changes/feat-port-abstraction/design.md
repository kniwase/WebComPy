## Context

WebComPy currently routes all browser API access through a single `browser` object (`_PyScriptBrowserModule`) that flattens the entire `js` (Pyodide) namespace into one module-like object. Eighteen consumer files import this object directly and guard every access with `if browser:` truthiness checks. This design has served well but has clear limitations:

- Testing DOM operations requires an actual browser (PyScript/Emscripten) environment
- The all-or-nothing `browser` monolith cannot distinguish "DOM manipulation" from "history navigation" from "HTTP requests"
- No server-side DOM can exist, forcing a parallel `_render_html()` HTML string generation path that diverges from the main render path
- Direct `import js` / `dir(js)` flattening bypasses PyScript's official `pyscript.context` and `pyscript.ffi` APIs, which provide thread-safe access and Worker support

The goal is to introduce function-specific port abstractions injected via the existing DI system, enabling:
1. Mock-based testing of all browser-API-dependent code
2. A unified `render()` path that works in both environments (phase 2: virtual DOM)
3. Use of official PyScript APIs (`pyscript.context`, `pyscript.ffi`, `pyscript.fetch`)
4. Clear separation of concerns between framework subsystems

## Goals / Non-Goals

**Goals:**
- Create typed port Protocol interfaces for DOM, FFI, HTTP, history, and cookie operations
- Inject port implementations into `WebComPyApp.di_scope` at bootstrap, selected by environment
- Replace all direct `browser` imports in framework code with `inject(PORT_KEY)` calls
- Enable unit testing of DOM/event/fetch/history/cookie logic via mock port injection
- Browser implementations use `pyscript.context` and `pyscript.ffi` as their foundation
- `DOMNode` becomes an explicit-method Protocol enabling dual-environment node implementations
- `Location` delegates history operations to `HistoryPort` via DI
- `Router` receives `Location` via constructor injection
- Remove the `browser` object entirely (no deprecation needed — unstable release)

**Non-Goals:**
- Virtual DOM tree construction (deferred to `feat-virtual-dom` change)
- Worker thread support (ports lay groundwork but won't be tested in Workers yet)
- ConsolePort or TimerPort (logging.py and asyncio handle these sufficiently)
- Plugin system for custom port implementations (ports are framework-internal for now)
- Raw Pyodide (non-PyScript) environment support (separate change)

## Decisions

### Decision 1: DOMNode as explicit-method Protocol

**Chosen**: `DOMNode` Protocol with explicit method signatures:
- Tree: `appendChild(child)`, `removeChild(child)`, `insertBefore(new, ref)`, `replaceChild(new, old)`, `remove()`
- Attributes: `setAttribute(name, value)`, `getAttribute(name)`, `removeAttribute(name)`, `hasAttribute(name)`, `getAttributeNames()`
- Events: `addEventListener(event, handler, capture=False)`, `removeEventListener(event, handler)`
- Content: `textContent` (get/set property), `nodeName` (property), `nodeType` (property)
- Children: `childNodes` returns `DOMNodeList` (supports `.length` and `__getitem__`)
- Metadata: `__webcompy_node__: bool`

`DOMNodeList` is a Protocol with `length: int` (property) and `__getitem__(index: int) -> DOMNode`.

**Rationale**: The current `__getattr__`/`__setattr__` Protocol requires the node to be a raw JS proxy object. An explicit Protocol allows both `BrowserDOMNode` (thin JS adapter) and `VirtualDOMNode` (server-side tree) to satisfy the same interface without code changes at the call site.

`addEventListener` includes `capture=False` to match existing call sites (`_element.py:67,110` which pass `False` as the third argument). `BrowserDOMPort` passes through to the JS API; `VirtualDOMNode` ignores it.

`childNodes` returns `DOMNodeList` (not a plain `list`) so both `.length` and indexing `[idx]` work identically across `BrowserDOMNode` (real JS NodeList) and `VirtualDOMNode` (custom list-like object).

**Alternative considered**: Opaque handle + all operations through DOMPort. Rejected because it would require rewriting hundreds of `node.appendChild(child)` calls to `dom_port.append_child(node, child)` and makes the code significantly more verbose.

### Decision 2: DOMPort as Factory + Query + Schedule (not full node API)

**Chosen**: DOMPort provides `create_element`, `create_text_node`, `query_selector`, `get_element_by_id`, `set_title`, and `schedule_macro_task`. Node operations (`appendChild`, `setAttribute`, etc.) live on `DOMNode` itself.

**Rationale**: Separating concerns keeps both interfaces small. `DOMPort` is the "document-level" gateway — creating nodes, querying the DOM, and providing scheduling. `DOMNode` is the "node-level" interface for tree manipulation. This maps naturally to the Web API where `document.createElement()` returns a node you then operate on directly.

**Alternative considered**: Everything on DOMPort. Rejected for verbosity reasons (see Decision 1).

### Decision 3: Port dependency pattern — app→port via inject(), intra-port via direct import

The framework code layer (elements, router, app, etc.) resolves ports through DI:
```python
dom = inject(DOM_PORT_KEY)  # framework code
```

Browser port implementations import each other directly within the same implementation layer:
```python
# BrowserDOMPort uses BrowserFFIPort directly
from webcompy.ports._browser._ffi import BrowserFFIPort
```

**Rationale**: App-layer code needs swappable implementations (browser vs server vs test mock). Browser-layer implementations are always deployed together and share the same runtime environment — they are implementation details of the browser platform, not independently swappable units.

**Alternative considered**: DI injection for port-to-port dependencies. Rejected because it creates unnecessary initialization ordering constraints, adds DI keys for internal implementation details, and over-abstracts dependencies that only exist within one platform layer.

### Decision 4: Browser implementations use pyscript.context + pyscript.ffi

**Chosen**: BrowserDOMPort uses `pyscript.context.document`/`pyscript.context.window`, BrowserFFIPort wraps `pyscript.ffi`, BrowserFetchPort wraps `pyscript.fetch`. BrowserHistoryPort uses `pyscript.context.window.history`/`pyscript.context.window.location`. BrowserCookiePort uses `pyscript.context.document.cookie`.

**Rationale**: These are the official PyScript APIs. `pyscript.context` transparently handles main thread vs Worker differences. `pyscript.ffi` works across Pyodide and MicroPython. The previous approach of `import js` / `dir(js)` flattening is a legacy pattern that bypasses these abstractions and only works in the main thread.

### Decision 5: Server implementations — Spy for phase 1, Virtual DOM for phase 2

**Phase 1 (this change)**: ServerDOMPort raises descriptive exceptions on node creation with clear messages. ServerFFIPort returns functions as-is (no proxy wrapping needed on server). ServerFetchPort uses `httpx` for actual HTTP requests. ServerHistoryPort stores path in a simple string attribute. ServerCookiePort parses Cookie headers and accumulates Set-Cookie headers.

**Phase 2 (future change)**: ServerDOMPort creates `VirtualDOMNode` instances that build an in-memory tree and generate HTML strings. This replaces the current `_render_html()` parallel path.

### Decision 6: DI key structure

DI keys defined in `webcompy/ports/_keys.py`:
```python
DOM_PORT_KEY = InjectKey[DOMPort]("webcompy-port-dom")
FFI_PORT_KEY = InjectKey[FFIPort]("webcompy-port-ffi")
FETCH_PORT_KEY = InjectKey[FetchPort]("webcompy-port-fetch")
COOKIE_PORT_KEY = InjectKey[CookiePort]("webcompy-port-cookie")
```

`HISTORY_PORT_KEY` lives in `webcompy/router/_keys.py` since HistoryPort is router-internal. All other keys are in `webcompy/ports/`.

### Decision 7: Directory structure

```
webcompy/ports/
├── __init__.py              # Public API: Protocol re-exports
├── _dom.py                  # DOMPort Protocol + DOMNode Protocol
├── _ffi.py                  # FFIPort Protocol
├── _fetch.py                # FetchPort Protocol + Response class
├── _cookie.py               # CookiePort Protocol
├── _keys.py                 # DI key definitions
├── _browser/
│   ├── __init__.py
│   ├── _dom.py              # BrowserDOMPort + BrowserDOMNode
│   ├── _ffi.py              # BrowserFFIPort
│   ├── _fetch.py            # BrowserFetchPort
│   └── _cookie.py           # BrowserCookiePort
└── _server/
    ├── __init__.py
    ├── _dom.py              # ServerDOMPort
    ├── _ffi.py              # ServerFFIPort
    ├── _fetch.py            # ServerFetchPort via httpx
    └── _cookie.py           # ServerCookiePort
```

`HistoryPort` Protocol at `webcompy/router/_history_port.py` (internal). Browser implementation at `webcompy/router/_browser_history.py`. Server implementation at `webcompy/router/_server_history.py`.

### Decision 8: HistoryPort as active abstraction — Location and RouterLink delegate to it

**Chosen**: `Location` no longer directly accesses `pyscript.context.window`. Instead, all history/location operations flow through `HistoryPort`:

```python
class Location(SignalBase[str]):
    def __init__(self, mode, base_url):
        self._popstate_handle = None
        self.set_mode(mode)
        if ENVIRONMENT == "pyscript":
            self._popstate_handle = inject(HISTORY_PORT_KEY).on_popstate(self._refresh_path)

    def _refresh_path(self, _=None):
        history = inject(HISTORY_PORT_KEY)
        path = history.current_path
        state = history.state
        self.__set_path__(path, state)

    def destroy(self):
        if self._popstate_handle is not None:
            inject(HISTORY_PORT_KEY).off_popstate(self._popstate_handle)
```

```python
# RouterLink._on_click
history = inject(HISTORY_PORT_KEY)
history.navigate(href, state)
```

**Rationale**: This achieves the original goal — browser and server share the same code path through `HistoryPort`. In the browser, `BrowserHistoryPort` delegates to `pyscript.context.window`. On the server, `ServerHistoryPort` stores path values internally. Unit tests can inject a mock `HistoryPort`.

**Alternative considered**: Direct `pyscript.context.window` access in Location. Rejected because it defeats the purpose of the port abstraction — it makes Location browser-specific code that cannot be unit tested without a real browser environment, and creates divergent code paths between browser and server.

### Decision 9: Router receives Location via constructor injection

**Chosen**: `Router` accepts `location: Location` as a required constructor parameter instead of creating `Location(self.__mode__, self.__base_url__)` internally:

```python
class Router:
    def __init__(self, *pages, location: Location, ...):
        self._location = location

# Bootstrap order in WebComPyApp.__init__:
# 1. Provide all ports into DI scope
# 2. Construct Location (within DI scope — inject(HISTORY_PORT_KEY) works)
# 3. Construct Router(location=location)
# 4. Construct AppDocumentRoot
```

**Rationale**: `Location.__init__` needs `inject(HISTORY_PORT_KEY)` which requires an active DI scope with `HistoryPort` provided. By moving Location construction after port provision, the DI lookup succeeds. This is a breaking change to `Router`'s public API, but acceptable for an unstable release.

**Alternative considered**: Lazy initialization (`Location.init()` called later). Rejected because it adds lifecycle complexity and makes the object temporarily invalid. Constructor injection is cleaner and more testable.

### Decision 10: Remove browser object entirely

**Chosen**: The `browser` object and `webcompy/_browser/` module are removed completely. No deprecation period — WebComPy is an unstable release.

**Rationale**: All framework code has been migrated to port injection. The `browser` object is dead code. A deprecation period serves no purpose when the framework doesn't guarantee backward compatibility.

### Decision 11: CookiePort for cross-environment cookie access

**Chosen**: `CookiePort` Protocol with methods `get(name)`, `set(name, value, *, max_age, path, secure, httponly, samesite)`, `delete(name, path)`, and `get_all()`.

Browser implementation delegates to `document.cookie`. Server implementation parses the `Cookie` request header and accumulates `Set-Cookie` headers.

**Rationale**: Cookies are needed for session management in SSR. A unified port abstraction allows framework code (e.g., authentication middleware) to work identically in both environments and be unit testable via mock injection.

## Migration pattern for `if browser:` branching logic

The current codebase uses `if browser:` for two distinct purposes. Each requires a different migration strategy.

**Pattern A — Guarding browser-only operations (most common):**
```python
# Before
if browser:
    browser.document.createElement("div")
else:
    raise WebComPyException(...)
# After
dom = inject(DOM_PORT_KEY)
dom.create_element("div")  # ServerDOMPort raises in phase 1, VirtualDOMNode in phase 2
```
No branching needed — the port handles the difference internally.

**Pattern B — Branching between browser and server rendering paths:**
```python
# Before (_switch.py, _repeat.py, _view.py, _dynamic.py, _component.py)
if browser:
    # Browser path: use setTimeout for deferred callbacks, real DOM mounting
else:
    # Server path: synchronous callbacks, no DOM mounting
# After (phase 1: feat-port-abstraction)
dom = inject(DOM_PORT_KEY)
dom.schedule_macro_task(callback)  # Browser: setTimeout, Server: synchronous
# Server-only shortcuts (_on_set_parent server branches) remain unchanged;
# they are addressed in phase 2 (feat-virtual-dom) when render() is unified.
```

For cases where code genuinely needs to know the current environment (e.g., deferring lifecycle hooks differently), use `ENVIRONMENT` from `webcompy.utils`:
```python
from webcompy.utils import ENVIRONMENT
if ENVIRONMENT == "pyscript":
    # browser-specific logic
```

## Risks / Trade-offs

- **[Large code change]** 18 files needed migration from `browser` to port injection. → Mitigation: phased migration — introduce ports alongside browser, migrate file by file, run full test suite after each.
- **[Performance]** BrowserDOMNode adapter adds one Python call layer per DOM operation. → Mitigation: adapter methods are thin one-liners delegating to JS objects; overhead is negligible compared to PyScript's existing proxy overhead.
- **[Breaking change]** `Router` API changes (requires `location` parameter). → Acceptable for unstable release.
- **[Breaking change]** `browser` object removed entirely. → Acceptable for unstable release; all consumers already migrated to ports.
- **[DOMNode Protocol size]** The explicit Protocol has ~20 methods. → Trade-off accepted: this is the standard DOM API surface needed by the element system. Extending `DOMNode` is rare.
