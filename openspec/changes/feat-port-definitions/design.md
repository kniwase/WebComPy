## Context

WebComPy currently routes all browser API access through a single `browser` object. Before replacing it, the replacement must exist. This phase adds port ABC definitions, dual-environment implementations, and DI keys as pure additive dead code — zero existing files are modified.

## Goals / Non-Goals

**Goals:**
- Create typed port abstract base classes (ABCs) for DOM, FFI, HTTP, history, and cookie operations
- Provide browser implementations using `pyscript.context` and `pyscript.ffi`
- Provide server implementations using `httpx` (FetchPort) and internal state (others)
- Define DI keys in `webcompy/ports/_keys.py` for all 5 ports
- Add `httpx` to `pyproject.toml`

**Non-Goals:**
- Migrate any existing consumers to use ports (subsequent phases)
- Remove the `browser` object (subsequent phases)
- Change the Router API (subsequent phases)
- Virtual DOM implementation (separate change)

## Decisions

### Decision 1: Ports as ABCs, not Protocols

**Chosen**: Ports are defined as Python ABCs with `@abstractmethod` declarations.

**Rationale**: ABCs enforce nominal subtyping — only explicit subclasses satisfy DI keys. `HistoryPort` extends `SignalBase[str]`, which requires inheritance. Protocols with structural subtyping would accept any object with matching method names accidentally.

### Decision 2: Package structure

**Chosen**:
```
webcompy/ports/
  __init__.py
  _keys.py           # DI keys for all 5 ports
  _dom.py            # DOMNode ABC + DOMPort ABC
  _ffi.py            # FFIPort ABC
  _fetch.py          # FetchPort ABC + Response dataclass
  _cookie.py         # CookiePort ABC
  _history.py        # HistoryPort ABC (extends SignalBase[str])
  _browser/
    __init__.py
    _dom.py          # BrowserDOMNode + BrowserDOMPort
    _ffi.py          # BrowserFFIPort
    _fetch.py        # BrowserFetchPort
    _cookie.py       # BrowserCookiePort
    _history.py      # BrowserHistoryPort
  _server/
    __init__.py
    _dom.py          # ServerDOMNode + ServerDOMPort
    _ffi.py          # ServerFFIPort
    _fetch.py        # ServerFetchPort (via httpx)
    _cookie.py       # ServerCookiePort
    _history.py      # ServerHistoryPort
```

### Decision 3: DOMNode as explicit-method ABC

DOMNode ABC with explicit method signatures replacing direct DOM property access:
- Tree: `appendChild`, `removeChild`, `insertBefore`, `replaceChild`, `remove`
- Attributes: `setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`
- Events: `addEventListener` (with `capture=False` default), `removeEventListener`
- Content: `textContent` (property), `childNodes` (property, returns `DOMNodeList`)
- WebComPy markers: `__webcompy_node__` and `__webcompy_prerendered_node__` (properties with setters)

`DOMNodeList` is a simple class (not ABC) with `length: int` (property) and `__getitem__(index: int) -> DOMNode`.

### Decision 4: Port dependency pattern — app→port via inject(), intra-port via direct import

Framework code resolves ports through DI: `dom = inject(DOM_PORT_KEY)`. Browser port implementations import each other directly within the same implementation layer. App-layer code needs swappable implementations (browser vs server vs test mock). Browser-layer implementations are always deployed together — they are implementation details of the browser platform, not independently swappable units.

### Decision 5: DI key naming convention

All DI keys in `webcompy/ports/_keys.py`:
```python
DOM_PORT_KEY = InjectKey[DOMPort]("webcompy-port-dom")
FFI_PORT_KEY = InjectKey[FFIPort]("webcompy-port-ffi")
FETCH_PORT_KEY = InjectKey[FetchPort]("webcompy-port-fetch")
COOKIE_PORT_KEY = InjectKey[CookiePort]("webcompy-port-cookie")
HISTORY_PORT_KEY = InjectKey[HistoryPort]("webcompy-port-history")
```

### Decision 6: HistoryPort extends SignalBase[str]

HistoryPort inherits `SignalBase[str]` to enable reactive path state. It has a concrete `value` property using `producer_accessed()`, plus abstract `current_search`, `history_state`, `navigate`, and `refresh_from_window` methods. Server implementation stores path internally; browser reads from `pyscript.context.window`.

### Decision 7: CookiePort API

CookiePort ABC with methods:
- `get(name: str) -> str | None`
- `set(name: str, value: str, *, max_age: int | None = None, path: str = "/", secure: bool = False, httponly: bool = False, samesite: str | None = None)`
- `delete(name: str, path: str = "/")`
- `get_all() -> dict[str, str]`

## Risks / Trade-offs

- [Risk] ABCs with `SignalBase` parent have version tracking overhead → Mitigation: only HistoryPort uses this; other ports are simple ABCs
- [Risk] Browser implementations import `pyscript` unconditionally but only execute in PyScript env → Mitigation: constructor lazily accesses `pyscript.context` guarded by `ENVIRONMENT`
