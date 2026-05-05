## Why

WebComPy currently accesses browser APIs through a single `browser` monolith object imported directly by 18 files across the codebase. This creates tight coupling: every piece of rendering, routing, HTTP, and logging code depends on one opaque object and guards every call with `if browser:` checks. Testing DOM operations requires an actual browser environment, server-side code crashes on any DOM access, and the abstraction is all-or-nothing — there is no way to provide mock implementations per capability.

Introducing function-specific port abstractions injected via DI separates browser API concerns (DOM, FFI, HTTP, history) into replaceable implementations. The same code runs identically in browser, server, and test environments by swapping the injected port implementation.

## What Changes

- **NEW** `webcompy/ports/` public package containing port Protocol definitions and DI keys
- **NEW** `DOMPort` abstraction: DOM node creation/manipulation, event listeners, title, and `setTimeout`-based macro-task scheduling via `schedule_macro_task`
- **NEW** `FFIPort` abstraction: Python↔JavaScript bridge (`create_proxy`, `destroy_proxy`, `is_none`, `to_js`, `assign`) backed by `pyscript.ffi` in the browser
- **NEW** `FetchPort` abstraction: HTTP requests backed by `pyscript.fetch` in the browser and `httpx` on the server
- **NEW** `HistoryPort` abstraction (router-internal, not public): browser history and location, backed by `pyscript.context.window` in the browser
- **MODIFIED** `DOMNode` Protocol: replaced loose `__getattr__`/`__setattr__` duck-typing with explicit method signatures (`appendChild`, `setAttribute`, `addEventListener`, `textContent`, etc.) enabling dual-environment implementations
- **MODIFIED** All 18 files currently importing `browser` migrated to inject ports via `inject(PORT_KEY)`
- **MODIFIED** `webcompy/_browser/` internals replaced by port implementations; `browser` re-export kept in `__init__.py` as **DEPRECATED** shim directing users to port APIs
- **MODIFIED** Environment detection consolidated: browser implementations use `pyscript.context.document`/`pyscript.context.window` and `pyscript.ffi` instead of direct `import js` / `dir(js)` flattening

## Capabilities

### New Capabilities

- `port-abstraction`: Function-specific port interfaces (DOMPort, FFIPort, FetchPort, HistoryPort) injected via DI with browser and server implementations, replacing the monolithic `browser` object and enabling mock-based testing of all browser-API-dependent code.

### Modified Capabilities

- `browser-api`: Major requirement changes — the `browser` object becomes a deprecated shim; all framework code accesses browser APIs through typed port Protocol interfaces with DI-injectable implementations instead of direct `if browser:`-guarded calls. Environment detection switches from `import js`/`dir(js)` flattening to `pyscript.context` and `pyscript.ffi`.

## Impact

- **Affected modules**: `webcompy/ports/` (new), `webcompy/_browser/` (refactored), all elements types, router, app, ajax, components, signal, aio, logging (~18 consumer files)
- **Breaking**: `browser` is **DEPRECATED** — direct consumers should migrate to port injection (`inject(DOM_PORT_KEY)` etc.). The `browser` object remains accessible during a deprecation period
- **Dependencies**: New production dependency `httpx` (server-side FetchPort), `pyscript.context` and `pyscript.ffi` become the standard browser API entry points
- **Testing**: All browser-dependent code becomes testable via mock port injection — no browser environment required for unit tests
