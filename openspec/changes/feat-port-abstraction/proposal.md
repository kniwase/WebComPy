## Why

WebComPy currently accesses browser APIs through a single `browser` monolith object imported directly by 18 files across the codebase. This creates tight coupling: every piece of rendering, routing, HTTP, and logging code depends on one opaque object and guards every call with `if browser:` checks. Testing DOM operations requires an actual browser environment, server-side code crashes on any DOM access, and the abstraction is all-or-nothing — there is no way to provide mock implementations per capability.

Introducing function-specific port abstractions (abstract base classes, not Protocols) injected via DI separates browser API concerns (DOM, FFI, HTTP, history, cookies) into replaceable implementations. The same code runs identically in browser, server, and test environments by swapping the injected port implementation.

## What Changes

- **NEW** `webcompy/ports/` public package containing port ABC definitions and DI keys
- **NEW** `DOMPort` (ABC): DOM node creation, element querying, title control, and `setTimeout`-based macro-task scheduling via `schedule_macro_task`
- **NEW** `DOMNode` (ABC): explicit-method node interface (`appendChild`, `setAttribute`, `addEventListener`, etc.) enabling dual-environment implementations (`BrowserDOMNode`, future `VirtualDOMNode`)
- **NEW** `FFIPort` (ABC): Python↔JavaScript bridge (`create_proxy`, `destroy_proxy`, `is_none`, `to_js`, `assign`) backed by `pyscript.ffi` in the browser
- **NEW** `FetchPort` (ABC): HTTP requests backed by `pyscript.fetch` in the browser and `httpx` on the server
- **NEW** `CookiePort` (ABC): cookie read/write/delete backed by `document.cookie` in the browser and HTTP header parsing/accumulation on the server
- **NEW** `HistoryPort` (ABC, extends `SignalBase[str]`): reactive history state + navigation operations. Absorbs the old `Location` class entirely. Browser implementation reads from `pyscript.context.window`; server stores path internally
- **REMOVED** `Location` class — all its functionality (SignalBase, popstate, path reading) is now part of `HistoryPort`
- **MODIFIED** `Router`: holds `HistoryPort` instead of `Location`
- **MODIFIED** `RouterLink`: `_on_click` navigates via `inject(HISTORY_PORT_KEY).navigate()`
- **MODIFIED** All 18 files currently importing `browser` migrated to inject ports via `inject(PORT_KEY)`
- **REMOVED** `webcompy/_browser/` module and the `browser` object — replaced entirely by port abstractions

## Capabilities

### New Capabilities

- `port-abstraction`: Function-specific port ABCs (DOMPort, DOMNode, FFIPort, FetchPort, CookiePort, HistoryPort) injected via DI with browser and server implementations, replacing the monolithic `browser` object and enabling mock-based testing of all browser-API-dependent code.

### Modified Capabilities

- `browser-api`: Major requirement changes — the `browser` object is **REMOVED**; all framework code accesses browser APIs through typed port ABCs with DI-injectable implementations. Environment detection switches from `import js`/`dir(js)` flattening to `pyscript.context` and `pyscript.ffi`.

## Impact

- **Affected modules**: `webcompy/ports/` (new), all elements types, router (HistoryPort replaces Location), app, ajax, components, signal, aio, logging (~20 consumer files + E2E test apps)
- **Breaking**: `browser` is **REMOVED** — replaced by port injection (`inject(DOM_PORT_KEY)` etc.)
- **Breaking**: `Location` is **REMOVED** — merged into `HistoryPort`. All Location references must be updated
- **Breaking**: `Router` no longer creates Location internally; references `self._history` (HistoryPort) instead
- **Dependencies**: New production dependency `httpx` (server-side FetchPort), `pyscript.context` and `pyscript.ffi` become the standard browser API entry points
- **Testing**: All browser-dependent code becomes testable via mock port injection — no browser environment required for unit tests
