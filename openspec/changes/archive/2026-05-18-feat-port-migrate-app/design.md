## Context

Phase 3 (`feat-port-migrate-consumers`) already provides `BrowserDOMPort`, `BrowserFFIPort`, and `BrowserFetchPort` in the PyScript branch of `WebComPyApp.__init__`. This phase adds the missing `HistoryPort` to that branch and provides all four server-side port implementations for the server branch. It also migrates `_root_component.py` away from `browser`.

## Goals / Non-Goals

**Goals:**
- PyScript branch: provide `BrowserHistoryPort` (in addition to existing DOM/FFI/Fetch ports)
- Server branch: provide `ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerHistoryPort`
- Migrate `_root_component.py`: replace `browser` access with `inject(DOM_PORT_KEY)` and `ENVIRONMENT` equivalents

**Non-Goals:**
- Remove existing `browser` imports (next phase)
- Change Router API (subsequent phase)

## Decisions

### Decision 1: Ports provided after imports, before `AppDocumentRoot`

Existing DOM/FFI/Fetch ports are already provided in the PyScript branch at import time. HistoryPort is added there. Server ports are provided in the server `else` block after `_register_deferred_components()`.

### Decision 2: `_root_component.py` replaces `browser` with `inject(DOM_PORT_KEY)`

All 16 `browser` access sites are replaced:
- `browser.document.title` → `inject(DOM_PORT_KEY).set_title(title)`
- `browser.document.querySelector(...)` → `inject(DOM_PORT_KEY).query_selector(...)`
- `browser.document.getElementById(...)` → `inject(DOM_PORT_KEY).get_element_by_id(...)`
- `browser.document.documentElement.*` → root element obtained via `inject(DOM_PORT_KEY).query_selector("html")`
- `if browser:` → `if ENVIRONMENT == "pyscript":`
- `browser.document.createElement(...)` / `browser.document.head.appendChild(...)` → via `inject(DOM_PORT_KEY).create_element(...)`

### Decision 3: `ServerHistoryPort` uses `mode="history"` for SSG

`ServerHistoryPort` is constructed with `mode="history"` (not `"hash"`). SSG generates clean URL paths without hash fragments, so history mode is the appropriate default for server-side rendering.

### Decision 4: `inject()` in `set_html_attr` callback lambda relies on DI scope fallback

The lambda callback registered via `value.on_after_updating()` calls `inject(DOM_PORT_KEY)`. In the PyScript environment the DI scope is entered at app init and never exited, so `inject()` always resolves. If the `ContextVar` binding is lost during a JS→Python callback, `inject()` falls back to `_get_app_di_scope()`, which also holds the ports. Either path resolves correctly.

## Risks / Trade-offs

- No risk — ports are not yet required by any component. Addition only.
