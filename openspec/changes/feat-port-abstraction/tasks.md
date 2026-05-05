## 1. Package scaffolding and DOMNode Protocol

- [ ] 1.1 Create `webcompy/ports/` package structure with `__init__.py` and sub-package directories (`_browser/`, `_server/`)
- [ ] 1.2 Add `httpx` as production dependency via `uv add httpx`
- [ ] 1.3 Define `DOMNode` Protocol in `webcompy/ports/_dom.py` with explicit method signatures: `appendChild`, `insertBefore`, `replaceChild`, `removeChild`, `remove`, `setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`, `addEventListener`, `removeEventListener`, `textContent`, `nodeName`, `nodeType`, `childNodes`, `__webcompy_node__`

## 2. DOMPort Protocol and implementations

- [ ] 2.1 Define `DOMPort` Protocol in `webcompy/ports/_dom.py` with methods: `create_element`, `create_text_node`, `query_selector`, `get_element_by_id`, `set_title`, `schedule_macro_task`
- [ ] 2.2 Implement `BrowserDOMNode` in `webcompy/ports/_browser/_dom.py` — thin adapter wrapping a JS DOM node, delegating all Protocol methods to the underlying JS object
- [ ] 2.3 Implement `BrowserDOMPort` in `webcompy/ports/_browser/_dom.py` — factory creating `BrowserDOMNode` instances via `pyscript.context.document`, query methods, `set_title`, and `schedule_macro_task` via `pyscript.context.window.setTimeout`
- [ ] 2.4 Implement `ServerDOMPort` in `webcompy/ports/_server/_dom.py` (phase 1) — `create_element` and `create_text_node` raise descriptive `WebComPyException`, `query_selector` and `get_element_by_id` return `None`, `set_title` is no-op, `schedule_macro_task` executes callback synchronously

## 3. FFIPort Protocol and implementations

- [ ] 3.1 Define `FFIPort` Protocol in `webcompy/ports/_ffi.py` with methods: `create_proxy`, `destroy_proxy`, `is_none`, `to_js`, `assign`
- [ ] 3.2 Implement `BrowserFFIPort` in `webcompy/ports/_browser/_ffi.py` — delegates to `pyscript.ffi.create_proxy`, `pyscript.ffi.is_none`, `pyscript.ffi.to_js`, `pyscript.ffi.assign`, and calls `.destroy()` on proxies
- [ ] 3.3 Implement `ServerFFIPort` in `webcompy/ports/_server/_ffi.py` — `create_proxy` returns the function as-is, `destroy_proxy` is no-op, `is_none` checks Python `None`, `to_js` returns value unchanged, `assign` merges dicts

## 4. FetchPort Protocol and implementations

- [ ] 4.1 Define `FetchPort` Protocol in `webcompy/ports/_fetch.py` with async `request` method accepting `method`, `url`, `headers`, `query_params`, `json`, `body_data`, `form_data`, `form_element` parameters
- [ ] 4.2 Implement `BrowserFetchPort` in `webcompy/ports/_browser/_fetch.py` — delegates to `pyscript.fetch`, handles JSON serialization, `FormData` construction, query param encoding, returns existing `Response` wrapper
- [ ] 4.3 Implement `ServerFetchPort` in `webcompy/ports/_server/_fetch.py` — delegates to `httpx.AsyncClient`, returns same `Response` wrapper, raises on `form_element` (browser-only feature)

## 5. HistoryPort (router-internal)

- [ ] 5.1 Define `HistoryPort` Protocol in `webcompy/router/_history_port.py` with methods: `current_path`, `current_search`, `navigate`, `on_popstate`, `off_popstate`, `state` (property)
- [ ] 5.2 Implement `BrowserHistoryPort` in `webcompy/router/_browser_history.py` — delegates to `pyscript.context.window.history` and `pyscript.context.window.location`, creates `pyscript.ffi` proxies for popstate listener
- [ ] 5.3 Implement `ServerHistoryPort` in `webcompy/router/_server_history.py` — stores path in a simple string, `on_popstate`/`off_popstate` are no-ops, `navigate` sets internal state

## 6. DI keys and bootstrap wiring

- [ ] 6.1 Define DI keys in `webcompy/ports/_keys.py`: `DOM_PORT_KEY`, `FFI_PORT_KEY`, `FETCH_PORT_KEY`
- [ ] 6.2 Define internal `HISTORY_PORT_KEY` in `webcompy/router/_keys.py` (alongside existing `_ROUTER_KEY`)
- [ ] 6.3 Wire port instantiation into `WebComPyApp.__init__` — create and provide all port implementations based on `ENVIRONMENT`, use existing `self._di_scope.provide()` pattern

## 7. Public API surface

- [ ] 7.1 Update `webcompy/ports/__init__.py` to re-export `DOMPort`, `FFIPort`, `FetchPort`, `DOMNode`, `Response`, and all DI keys
- [ ] 7.2 Update `webcompy/__init__.py` to import and export the `ports` module, add port classes/keys to `__all__`

## 8. Migrate element system

- [ ] 8.1 Migrate `webcompy/elements/types/_element.py` — replace `from webcompy._browser._modules import browser` with `inject(DOM_PORT_KEY)` and `inject(FFI_PORT_KEY)` for DOM operations and event proxy creation/destruction
- [ ] 8.2 Migrate `webcompy/elements/types/_text.py` — use `dom_port.create_text_node()` and `dom_port.create_element("br")`, remove `browser` guards
- [ ] 8.3 Migrate `webcompy/elements/types/_abstract.py` — use `dom_port.create_text_node("")` for placeholder node creation in `_detach_node`
- [ ] 8.4 Migrate `webcompy/elements/types/_switch.py` — use `dom_port.schedule_macro_task()` instead of `browser.window.setTimeout`
- [ ] 8.5 Migrate `webcompy/elements/types/_repeat.py` — use `inject(DOM_PORT_KEY)` for `browser` truthiness checks
- [ ] 8.6 Migrate `webcompy/elements/types/_dynamic.py` — remove `browser` import, use port injection

## 9. Migrate router module

- [ ] 9.1 Migrate `webcompy/router/_change_event_handler.py` — use injected `FFIPort` and `HistoryPort` instead of direct `browser.pyscript.ffi.*` and `browser.window.*` calls
- [ ] 9.2 Migrate `webcompy/router/_link.py` — use `HistoryPort.navigate()` instead of `browser.window.history.pushState()` and `browser.window.location.*`
- [ ] 9.3 Migrate `webcompy/router/_router.py` — use `dom_port.schedule_macro_task()` in `preload_lazy_routes` instead of `browser.window.setTimeout()`
- [ ] 9.4 Migrate `webcompy/router/_lazy.py` — use port injection for `browser.console.warn` preload error logging
- [ ] 9.5 Migrate `webcompy/router/_view.py` — use `inject(DOM_PORT_KEY)` instead of `browser` truthiness check

## 10. Migrate app, components, signal, aio, logging

- [ ] 10.1 Migrate `webcompy/app/_root_component.py` — use `dom_port.query_selector()`, `dom_port.get_element_by_id()`, `dom_port.set_title()` instead of `browser.document.*`
- [ ] 10.2 Migrate `webcompy/app/_app.py` — port providing is done in task 6.3; update `_emit_profile_summary` to use `inject()` instead of direct `browser` import
- [ ] 10.3 Migrate `webcompy/components/_component.py` — remove `browser` import, use port injection for truthiness check
- [ ] 10.4 Migrate `webcompy/signal/_effect.py` — use `inject(DOM_PORT_KEY).schedule_macro_task()` instead of `browser.window.setTimeout()`
- [ ] 10.5 Migrate `webcompy/aio/_aio.py` — remove `browser` import, use `ENVIRONMENT` condition from `webcompy.utils` for asyncio resolver selection
- [ ] 10.6 Migrate `webcompy/logging.py` — keep `browser` fallback but add deprecation path; logging handler selection unchanged

## 11. Migrate ajax (HttpClient → FetchPort)

- [ ] 11.1 Refactor `webcompy/ajax/_fetch.py` — `HttpClient` methods delegate to `inject(FETCH_PORT_KEY).request()`, remove direct `browser.fetch` and `browser.pyscript.ffi` usage
- [ ] 11.2 Move `Response` and `WebComPyHttpClientException` to `webcompy/ports/_fetch.py` (single source of truth); `ajax/_fetch.py` re-exports from there

## 12. Deprecate browser object

- [ ] 12.1 Add deprecation mechanism — `webcompy/_browser/_modules.py` emits `DeprecationWarning` on import when accessed from non-port code (keep existing `browser` functionality intact during deprecation period)
- [ ] 12.2 Update `webcompy/__init__.py` `browser` export to go through deprecation-aware import path

## 13. Tests

- [ ] 13.1 Create `MockDOMPort` and `MockDOMNode` spy implementations in `tests/` — record all operations for assertion
- [ ] 13.2 Create `MockFFIPort` spy implementation — record `create_proxy`/`destroy_proxy` calls
- [ ] 13.3 Create `MockFetchPort` spy implementation — record requests and return canned responses
- [ ] 13.4 Write tests for `BrowserDOMPort` node creation and attribute operations
- [ ] 13.5 Write tests for `ServerFetchPort` HTTP request delegation through `httpx`
- [ ] 13.6 Write tests for element system with `MockDOMPort` injected — verify correct DOM API calls during rendering
- [ ] 13.7 Write tests for router `Location` with `MockFFIPort` and `MockHistoryPort` injected
- [ ] 13.8 Run existing test suite and fix regressions

## 14. Verification

- [ ] 14.1 Run lint: `uv run ruff check .`
- [ ] 14.2 Run type check: `uv run pyright`
- [ ] 14.3 Run unit tests: `uv run python -m pytest tests/ --tb=short`
- [ ] 14.4 Verify dev server starts and renders: `uv run python -m webcompy start --dev --app docs_app.bootstrap:app`
