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
- Create typed port abstract base classes (ABCs) for DOM, FFI, HTTP, history, and cookie operations
- Inject port implementations into `WebComPyApp.di_scope` at bootstrap, selected by environment
- Replace all direct `browser` imports in framework code with `inject(PORT_KEY)` calls
- Enable unit testing of DOM/event/fetch/history/cookie logic via mock port injection
- Browser implementations use `pyscript.context` and `pyscript.ffi` as their foundation
- `DOMNode` as an explicit-method ABC enabling dual-environment node implementations
- Merge `Location` into `HistoryPort` — one ABC for both reactive state and navigation operations
- Remove the `browser` object entirely (no deprecation needed — unstable release)

**Non-Goals:**
- Virtual DOM tree construction (deferred to `feat-virtual-dom` change)
- Worker thread support (ports lay groundwork but won't be tested in Workers yet)
- ConsolePort or TimerPort (logging.py and asyncio handle these sufficiently)
- Plugin system for custom port implementations (ports are framework-internal for now)
- Raw Pyodide (non-PyScript) environment support (separate change)

## Decisions

### Decision 1: Ports as abstract base classes, not Protocols

**Chosen**: Ports are defined as Python abstract base classes (`ABC`) with `@abstractmethod` declarations instead of `typing.Protocol`.

**Rationale**: Protocols enforce structural subtyping — any object with matching method names satisfies the type, even accidentally. ABCs enforce nominal subtyping — only explicit subclasses satisfy the type. This matters for DI because `InjectKey[DOMPort]` should only accept objects that intentionally implement the port contract, not any object that happens to have a `create_element` method. Additionally, `HistoryPort` needs to extend `SignalBase[str]` (for reactive path state), which requires inheritance — ABCs support this naturally while Protocols do not.

**Alternative considered**: Protocols with `@runtime_checkable`. Rejected because they provide weaker guarantees in a DI system where the injected implementation is determined at bootstrap, not at type-check time.

### Decision 2: DOMNode as explicit-method ABC

**Chosen**: `DOMNode` ABC with explicit method signatures:
- Tree: `appendChild(child)`, `removeChild(child)`, `insertBefore(new, ref)`, `replaceChild(new, old)`, `remove()`
- Attributes: `setAttribute(name, value)`, `getAttribute(name)`, `removeAttribute(name)`, `hasAttribute(name)`, `getAttributeNames()`
- Events: `addEventListener(event, handler, capture=False)`, `removeEventListener(event, handler)`
- Content: `textContent` (get/set property), `nodeName` (property), `nodeType` (property)
- Children: `childNodes` returns `DOMNodeList` (supports `.length` and `__getitem__`)
- Metadata: `__webcompy_node__: bool`

`DOMNodeList` is a simple class with `length: int` (property) and `__getitem__(index: int) -> DOMNode`.

**Rationale**: The old `__getattr__`/`__setattr__` catch-all required the node to be a raw JS proxy object. An explicit ABC allows both `BrowserDOMNode` (thin JS adapter) and `VirtualDOMNode` (server-side tree) to implement the same interface without code changes at the call site.

`addEventListener` includes `capture=False` to match existing call sites (`_element.py:67,110` which pass `False` as the third argument). `BrowserDOMPort` passes through to the JS API; `VirtualDOMNode` ignores it.

**Alternative considered**: Opaque handle + all operations through DOMPort. Rejected because it would require rewriting hundreds of `node.appendChild(child)` calls to `dom_port.append_child(node, child)`.

### Decision 3: DOMPort as Factory + Query + Schedule (not full node API)

**Chosen**: DOMPort provides `create_element`, `create_text_node`, `query_selector`, `get_element_by_id`, `set_title`, and `schedule_macro_task`. Node operations (`appendChild`, `setAttribute`, etc.) live on `DOMNode` itself.

**Rationale**: Separating concerns keeps both interfaces small. `DOMPort` is the "document-level" gateway — creating nodes, querying the DOM, and providing scheduling. `DOMNode` is the "node-level" interface for tree manipulation. This maps naturally to the Web API where `document.createElement()` returns a node you then operate on directly.

### Decision 4: Port dependency pattern — app→port via inject(), intra-port via direct import

The framework code layer (elements, router, app, etc.) resolves ports through DI:
```python
dom = inject(DOM_PORT_KEY)  # framework code
```

Browser port implementations import each other directly within the same implementation layer. App-layer code needs swappable implementations (browser vs server vs test mock). Browser-layer implementations are always deployed together and share the same runtime environment — they are implementation details of the browser platform, not independently swappable units.

### Decision 5: Browser implementations use pyscript.context + pyscript.ffi

**Chosen**: BrowserDOMPort uses `pyscript.context.document`/`pyscript.context.window`, BrowserFFIPort wraps `pyscript.ffi`, BrowserFetchPort wraps `pyscript.fetch`. BrowserHistoryPort uses `pyscript.context.window.history`/`pyscript.context.window.location`. BrowserCookiePort uses `pyscript.context.document.cookie`.

**Rationale**: These are the official PyScript APIs. `pyscript.context` transparently handles main thread vs Worker differences. `pyscript.ffi` works across Pyodide and MicroPython. The previous approach of `import js` / `dir(js)` flattening is a legacy pattern.

### Decision 6: Server implementations — Spy for phase 1, Virtual DOM for phase 2

**Phase 1 (this change)**: ServerDOMPort raises descriptive exceptions on node creation. ServerFFIPort returns functions as-is. ServerFetchPort uses `httpx`. ServerHistoryPort stores path in a simple string. ServerCookiePort parses Cookie headers and accumulates Set-Cookie headers.

**Phase 2 (future: feat-virtual-dom)**: ServerDOMPort creates `VirtualDOMNode` instances. HistoryPort's server path management integrates with the SSR rendering pipeline.

### Decision 7: Merge Location into HistoryPort

**Chosen**: `Location` (a `SignalBase[str]` subclass that reads `window.location` and monitors popstate) is absorbed into `HistoryPort`. `HistoryPort` extends `SignalBase[str]` and provides:

```python
class HistoryPort(SignalBase[str]):
    @property
    def current_search(self) -> str: ...
    @property
    def history_state(self) -> dict | None: ...
    def navigate(self, url: str, state: dict | None = None) -> None: ...
```

- Browser: `navigate()` calls `pushState` then updates `self.value` (triggers reactive propagation). `_refresh_from_window()` reads `window.location` on popstate. Constructor registers a `popstate` listener via `pyscript.ffi`.
- Server: `navigate()` sets `self.value` directly. No window access.

`Router` holds `self._history: HistoryPort` (instead of `self._location: Location`). `RouterLink._on_click` calls `inject(HISTORY_PORT_KEY).navigate(href, state)`.

**Rationale**: `Location` and `HistoryPort` had overlapping responsibilities — Location held the reactive state, HistoryPort provided the operations. Merging them eliminates the artificial split, reduces DI keys from 2 to 1, and makes dependency graphs simpler (Router only needs `HistoryPort`, not both).

**Alternative considered**: Keeping Location separate. Rejected because it created unnecessary indirection — all Location consumers also needed HistoryPort, and the two abstractions were never independently swappable.

### Decision 8: DI key structure

All DI keys in `webcompy/ports/_keys.py`:
```python
DOM_PORT_KEY = InjectKey[DOMPort]("webcompy-port-dom")
FFI_PORT_KEY = InjectKey[FFIPort]("webcompy-port-ffi")
FETCH_PORT_KEY = InjectKey[FetchPort]("webcompy-port-fetch")
COOKIE_PORT_KEY = InjectKey[CookiePort]("webcompy-port-cookie")
HISTORY_PORT_KEY = InjectKey[HistoryPort]("webcompy-port-history")
```

`HistoryPort` is a public port like the others — it is not router-internal.

### Decision 9: Directory structure

```
webcompy/ports/
├── __init__.py              # Public API: ABC re-exports + DI keys
├── _dom.py                  # DOMPort ABC + DOMNode ABC + DOMNodeList
├── _ffi.py                  # FFIPort ABC
├── _fetch.py                # FetchPort ABC + Response class
├── _cookie.py               # CookiePort ABC
├── _history.py              # HistoryPort ABC (extends SignalBase[str])
├── _keys.py                 # All DI key definitions
├── _browser/
│   ├── __init__.py
│   ├── _dom.py              # BrowserDOMPort + BrowserDOMNode
│   ├── _ffi.py              # BrowserFFIPort
│   ├── _fetch.py            # BrowserFetchPort
│   ├── _cookie.py           # BrowserCookiePort
│   └── _history.py          # BrowserHistoryPort
└── _server/
    ├── __init__.py
    ├── _dom.py              # ServerDOMPort
    ├── _ffi.py              # ServerFFIPort
    ├── _fetch.py            # ServerFetchPort
    ├── _cookie.py           # ServerCookiePort
    └── _history.py          # ServerHistoryPort
```

No more `webcompy/router/_history_port.py`, `_browser_history.py`, `_server_history.py` — HistoryPort lives in `ports/` like all other ports.

### Decision 10: Migration pattern for `if browser:` branching logic

**Pattern A — Guarding browser-only operations:**
```python
# Before
if browser:
    browser.document.createElement("div")
else:
    raise WebComPyException(...)
# After
inject(DOM_PORT_KEY).create_element("div")  # ServerDOMPort raises
```

**Pattern B — Branching between browser and server rendering paths:**
```python
# Before
if browser:
    browser.window.setTimeout(callback, 0)
# After
inject(DOM_PORT_KEY).schedule_macro_task(callback)  # Browser: setTimeout, Server: sync
```

**Pattern C — Environment-dependent behavior not covered by ports:**
```python
from webcompy.utils import ENVIRONMENT
if ENVIRONMENT == "pyscript":
    # browser-specific rendering logic
```

### Decision 11: CookiePort for cross-environment cookie access

`CookiePort` ABC with methods `get(name)`, `set(name, value, *, max_age, path, secure, httponly, samesite)`, `delete(name, path)`, and `get_all()`.

Browser implementation delegates to `document.cookie`. Server implementation parses the `Cookie` request header and accumulates `Set-Cookie` headers for response.

### Decision 12: Remove browser object entirely

The `browser` object and `webcompy/_browser/` module are removed completely. No deprecation period — WebComPy is an unstable release. All framework code has been migrated to port injection.

## Risks / Trade-offs

- **[Large code change]** 20+ files migrated. → Mitigation: ports introduced alongside browser, migrated file by file, full test suite after each.
- **[Performance]** BrowserDOMNode adapter adds one Python call layer per DOM operation. → Mitigation: thin one-liner delegation; overhead negligible compared to PyScript's existing proxy overhead.
- **[Breaking change]** `browser` removed, `Location` removed, `Router` internal API changed. → Acceptable for unstable release.
- **[Breaking change]** Apps that instantiate `Location` directly must switch to `HistoryPort`. → Acceptable for unstable release.
