## Context

WebComPy currently routes all browser API access through a single `browser` object (`_PyScriptBrowserModule`) that flattens the entire `js` (Pyodide) namespace into one module-like object. Twenty files import this object directly and guard every access with `if browser:` truthiness checks. This design has served well but has clear limitations:

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
- Create typed port Protocol interfaces for DOM, FFI, HTTP, and history operations
- Inject port implementations into `WebComPyApp.di_scope` at bootstrap, selected by environment
- Replace all direct `browser` imports in framework code with `inject(PORT_KEY)` calls
- Enable unit testing of DOM/event/fetch logic via mock port injection
- Browser implementations use `pyscript.context` and `pyscript.ffi` as their foundation
- `DOMNode` becomes an explicit-method Protocol enabling dual-environment node implementations

**Non-Goals:**
- Virtual DOM tree construction (deferred to `feat-virtual-dom` change)
- Worker thread support (ports lay groundwork but won't be tested in Workers yet)
- ConsolePort or TimerPort (logging.py and asyncio handle these sufficiently)
- Plugin system for custom port implementations (ports are framework-internal for now)
- Removing `browser` from the public API entirely (deprecated shim, not removal)

## Decisions

### Decision 1: DOMNode as explicit-method Protocol

**Chosen**: `DOMNode` Protocol with explicit method signatures (`appendChild`, `setAttribute`, `addEventListener`, `textContent`, `nodeName`, etc.)

**Rationale**: The current `__getattr__`/`__setattr__` Protocol requires the node to be a raw JS proxy object. An explicit Protocol allows both `BrowserDOMNode` (thin JS adapter) and `VirtualDOMNode` (server-side tree) to satisfy the same interface without code changes at the call site. This preserves the existing `node.method()` call pattern across the entire element system.

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

**Rationale**: App-layer code needs swappable implementations (browser vs server vs test mock). Browser-layer implementations are always deployed together and share the same runtime environment — they are implementation details of the browser platform, not independently swappable units. This matches Angular's pattern where `Renderer2` is injected but its internal use of `document` is direct.

**Alternative considered**: DI injection for port-to-port dependencies. Rejected because it creates unnecessary initialization ordering constraints, adds DI keys for internal implementation details, and over-abstracts dependencies that only exist within one platform layer.

### Decision 4: Browser implementations use pyscript.context + pyscript.ffi

**Chosen**: BrowserDOMPort uses `pyscript.context.document`/`pyscript.context.window`, BrowserFFIPort wraps `pyscript.ffi`, BrowserFetchPort wraps `pyscript.fetch`.

**Rationale**: These are the official PyScript APIs. `pyscript.context` transparently handles main thread vs Worker differences. `pyscript.ffi` works across Pyodide and MicroPython. The current approach of `import js` / `dir(js)` flattening is a legacy pattern that bypasses these abstractions and only works in the main thread.

### Decision 5: Server implementations — Spy for phase 1, Virtual DOM for phase 2

**Phase 1 (this change)**: ServerDOMPort raises descriptive exceptions on node creation with clear messages. ServerFFIPort returns functions as-is (no proxy wrapping needed on server). ServerFetchPort uses `httpx` for actual HTTP requests. ServerHistoryPort stores path in a simple string attribute.

**Phase 2 (future change)**: ServerDOMPort creates `VirtualDOMNode` instances that build an in-memory tree and generate HTML strings. This replaces the current `_render_html()` parallel path.

### Decision 6: DI key structure

Five internal DI keys defined in `webcompy/ports/_keys.py`:

```python
DOM_PORT_KEY = InjectKey[DOMPort]("webcompy-port-dom")
FFI_PORT_KEY = InjectKey[FFIPort]("webcompy-port-ffi")
FETCH_PORT_KEY = InjectKey[FetchPort]("webcompy-port-fetch")
HISTORY_PORT_KEY = InjectKey[HistoryPort]("webcompy-port-history")
```

`HistoryPort` and its key live in `webcompy/router/` since it is router-internal. All other keys are in `webcompy/ports/`.

### Decision 7: Directory structure

```
webcompy/ports/
├── __init__.py              # Public API: Protocol re-exports
├── _dom.py                  # DOMPort Protocol + DOMNode Protocol
├── _ffi.py                  # FFIPort Protocol
├── _fetch.py                # FetchPort Protocol
├── _keys.py                 # DI key definitions
├── _browser/
│   ├── __init__.py
│   ├── _dom.py              # BrowserDOMPort + BrowserDOMNode
│   ├── _ffi.py              # BrowserFFIPort
│   └── _fetch.py            # BrowserFetchPort
└── _server/
    ├── __init__.py
    ├── _dom.py              # ServerDOMPort
    ├── _ffi.py              # ServerFFIPort
    └── _fetch.py            # ServerFetchPort via httpx
```

`HistoryPort` Protocol at `webcompy/router/_history_port.py` (internal). Browser implementation at `webcompy/router/_browser_history_port.py`. Server implementation inline or in `webcompy/router/_server_history_port.py`.

## Risks / Trade-offs

- **[Large code change]** 20 files need migration from `browser` to port injection. → Mitigation: phased migration — introduce ports alongside browser, migrate file by file, run full test suite after each.
- **[Performance]** BrowserDOMNode adapter adds one Python call layer per DOM operation. → Mitigation: adapter methods are thin one-liners delegating to JS objects; overhead is negligible compared to PyScript's existing proxy overhead.
- **[Backward compatibility]** `browser` is part of `webcompy.__all__` and directly used by applications. → Mitigation: keep `browser` as deprecated shim during migration period with `DeprecationWarning` pointing to port APIs.
- **[DOMNode Protocol size]** The explicit Protocol has ~20 methods. → Trade-off accepted: this is the standard DOM API surface needed by the element system. Extending `DOMNode` is rare.
