## Why

WebComPy currently accesses browser APIs through a single `browser` monolith object imported directly by 18 files across the codebase. This creates tight coupling: every piece of rendering, routing, HTTP, and logging code depends on one opaque object and guards every call with `if browser:` checks. Testing DOM operations requires an actual browser environment, server-side code crashes on any DOM access, and the abstraction is all-or-nothing — there is no way to provide mock implementations per capability.

Introducing function-specific port abstractions injected via DI separates browser API concerns (DOM, FFI, HTTP, history, cookies) into replaceable implementations. The same code runs identically in browser, server, and test environments by swapping the injected port implementation.

## What Changes

- **NEW** `webcompy/ports/` public package containing port Protocol definitions and DI keys
- **NEW** `DOMPort` abstraction: DOM node creation/manipulation, event listeners, title, and `setTimeout`-based macro-task scheduling via `schedule_macro_task`
- **NEW** `FFIPort` abstraction: Python↔JavaScript bridge (`create_proxy`, `destroy_proxy`, `is_none`, `to_js`, `assign`) backed by `pyscript.ffi` in the browser
- **NEW** `FetchPort` abstraction: HTTP requests backed by `pyscript.fetch` in the browser and `httpx` on the server
- **NEW** `CookiePort` abstraction: cookie read/write/delete backed by `document.cookie` in the browser and HTTP header parsing/accumulation on the server
- **NEW** `HistoryPort` abstraction (router-internal): browser history and location, backed by `pyscript.context.window`. Actively used by `Location` and `RouterLink` via DI, replacing direct `pyscript.context.window` access in those components
- **MODIFIED** `DOMNode` Protocol: replaced loose `__getattr__`/`__setattr__` duck-typing with explicit method signatures enabling dual-environment implementations
- **MODIFIED** `Location`: refactored to delegate all history operations to `HistoryPort` via `inject(HISTORY_PORT_KEY)`
- **MODIFIED** `RouterLink`: `_on_click` navigates via `inject(HISTORY_PORT_KEY).navigate()` instead of directly accessing `pyscript.context.window`
- **MODIFIED** `Router`: accepts `Location` as a constructor parameter (breaking API change), enabling Location construction after DI scope is active
- **MODIFIED** All 18 files currently importing `browser` migrated to inject ports via `inject(PORT_KEY)`
- **REMOVED** `webcompy/_browser/` module and the `browser` object — replaced entirely by port abstractions

## Capabilities

### New Capabilities

- `port-abstraction`: Function-specific port interfaces (DOMPort, FFIPort, FetchPort, CookiePort, HistoryPort) injected via DI with browser and server implementations, replacing the monolithic `browser` object and enabling mock-based testing of all browser-API-dependent code.

### Modified Capabilities

- `browser-api`: Major requirement changes — the `browser` object is **REMOVED**; all framework code accesses browser APIs through typed port Protocol interfaces with DI-injectable implementations. Environment detection switches from `import js`/`dir(js)` flattening to `pyscript.context` and `pyscript.ffi`.

## Impact

- **Affected modules**: `webcompy/ports/` (new), all elements types, router (Location, RouterLink, Router), app, ajax, components, signal, aio, logging (~20 consumer files)
- **Breaking**: `browser` is **REMOVED** — replaced by port injection (`inject(DOM_PORT_KEY)` etc.)
- **Breaking**: `Router` constructor now requires `location: Location` parameter
- **Dependencies**: New production dependency `httpx` (server-side FetchPort), `pyscript.context` and `pyscript.ffi` become the standard browser API entry points
- **Testing**: All browser-dependent code becomes testable via mock port injection — no browser environment required for unit tests
