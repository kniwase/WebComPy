## 1. Package scaffolding and DOMNode Protocol

- [x] 1.1 Create `webcompy/ports/` package structure with `__init__.py` and sub-package directories (`_browser/`, `_server/`)
- [x] 1.2 Add `httpx` as production dependency via `uv add httpx`
- [x] 1.3 Define `DOMNode` and `DOMNodeList` Protocol in `webcompy/ports/_dom.py` with explicit method signatures: `appendChild`, `insertBefore`, `replaceChild`, `removeChild`, `remove`, `setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`, `addEventListener` (with `capture=False`), `removeEventListener`, `textContent`, `nodeName`, `nodeType`, `childNodes` (returns `DOMNodeList` with `.length` and `__getitem__`), `__webcompy_node__`

## 2. DOMPort Protocol and implementations

- [x] 2.1 Define `DOMPort` Protocol in `webcompy/ports/_dom.py` with methods: `create_element`, `create_text_node`, `query_selector`, `get_element_by_id`, `set_title`, `schedule_macro_task`
- [x] 2.2 Implement `BrowserDOMNode` in `webcompy/ports/_browser/_dom.py` — thin adapter wrapping a JS DOM node, delegating all Protocol methods to the underlying JS object
- [x] 2.3 Implement `BrowserDOMPort` in `webcompy/ports/_browser/_dom.py` — factory creating `BrowserDOMNode` instances via `pyscript.context.document`, query methods, `set_title`, and `schedule_macro_task` via `pyscript.context.window.setTimeout`
- [x] 2.4 Implement `ServerDOMPort` in `webcompy/ports/_server/_dom.py` (phase 1) — `create_element` and `create_text_node` raise descriptive `WebComPyException`, `query_selector` and `get_element_by_id` return `None`, `set_title` is no-op, `schedule_macro_task` executes callback synchronously

## 3. FFIPort Protocol and implementations

- [x] 3.1 Define `FFIPort` Protocol in `webcompy/ports/_ffi.py` with methods: `create_proxy`, `destroy_proxy`, `is_none`, `to_js`, `assign`
- [x] 3.2 Implement `BrowserFFIPort` in `webcompy/ports/_browser/_ffi.py` — delegates to `pyscript.ffi.create_proxy`, `pyscript.ffi.is_none`, `pyscript.ffi.to_js`, `pyscript.ffi.assign`, and calls `.destroy()` on proxies
- [x] 3.3 Implement `ServerFFIPort` in `webcompy/ports/_server/_ffi.py` — `create_proxy` returns the function as-is, `destroy_proxy` is no-op, `is_none` checks Python `None`, `to_js` returns value unchanged, `assign` merges dicts

## 4. FetchPort Protocol and implementations

- [x] 4.1 Define `FetchPort` Protocol in `webcompy/ports/_fetch.py` with async `request` method accepting `method`, `url`, `headers`, `query_params`, `json`, `body_data`, `form_data`, `form_element` parameters
- [x] 4.2 Implement `BrowserFetchPort` in `webcompy/ports/_browser/_fetch.py` — delegates to `pyscript.fetch`, handles JSON serialization, `FormData` construction, query param encoding, returns existing `Response` wrapper
- [x] 4.3 Implement `ServerFetchPort` in `webcompy/ports/_server/_fetch.py` — delegates to `httpx.AsyncClient`, returns same `Response` wrapper, raises on `form_element` (browser-only feature)

## 5. CookiePort Protocol and implementations (NEW)

- [ ] 5.1 Define `CookiePort` Protocol in `webcompy/ports/_cookie.py` with methods: `get(name) -> str | None`, `set(name, value, *, max_age=None, path="/", secure=False, httponly=False, samesite=None)`, `delete(name, path="/")`, `get_all() -> dict[str, str]`
- [ ] 5.2 Implement `BrowserCookiePort` in `webcompy/ports/_browser/_cookie.py` — delegates to `pyscript.context.document.cookie`, parses cookie string into dict for `get`/`get_all`, serializes for `set`/`delete`
- [ ] 5.3 Implement `ServerCookiePort` in `webcompy/ports/_server/_cookie.py` — parses `Cookie` request header for `get`/`get_all`, accumulates `Set-Cookie` response headers for `set`/`delete`

## 6. HistoryPort — rewrite for active use

- [ ] 6.1 Refactor `BrowserHistoryPort` in `webcompy/router/_browser_history.py` — remove `set_mode()` statefulness; `current_path` and `current_search` always read from `pyscript.context.window.location` based on `mode` parameter passed to each call; `on_popstate` creates a `pyscript.ffi` proxy and adds a `popstate` listener via `pyscript.context.window`; `off_popstate` removes the listener and destroys the proxy; `navigate` calls `window.history.pushState`
- [ ] 6.2 Update `HistoryPort` Protocol in `webcompy/router/_history_port.py` — add `mode` parameter to methods that need path/URL mode awareness: `current_path(mode: str) -> str`, `current_search() -> str`, `state(mode: str) -> dict | None`, `navigate(url: str, state: dict | None = None, mode: str = "hash") -> None`, `on_popstate(callback, mode: str) -> Any`, `off_popstate(handle: Any, mode: str) -> None`
- [ ] 6.3 Update `ServerHistoryPort` in `webcompy/router/_server_history.py` — match the updated Protocol; store path internally for `current_path`/`navigate`; `on_popstate`/`off_popstate` are no-ops; `state` returns None

## 7. DI keys and bootstrap wiring

- [x] 7.1 Define DI keys in `webcompy/ports/_keys.py`: `DOM_PORT_KEY`, `FFI_PORT_KEY`, `FETCH_PORT_KEY`
- [ ] 7.2 Add `COOKIE_PORT_KEY` to `webcompy/ports/_keys.py`
- [x] 7.3 Define `HISTORY_PORT_KEY` in `webcompy/router/_keys.py`
- [ ] 7.4 Rewire `WebComPyApp.__init__` bootstrap ordering — (1) provide all ports into DI scope, (2) construct `Location` within active DI scope, (3) construct `Router(location=location)`, (4) construct `AppDocumentRoot`

## 8. Public API surface

- [x] 8.1 Update `webcompy/ports/__init__.py` to re-export `DOMPort`, `FFIPort`, `FetchPort`, `DOMNode`, `Response`, and all DI keys
- [ ] 8.2 Add `CookiePort` and `COOKIE_PORT_KEY` to `webcompy/ports/__init__.py` re-exports
- [x] 8.3 Update `webcompy/__init__.py` to import and export the `ports` module, add port classes/keys to `__all__`, remove `browser` export

## 9. Location refactoring — delegate to HistoryPort

- [ ] 9.1 Rewrite `Location.__init__` — remove direct `pyscript.ffi.create_proxy` + `context.window.addEventListener("popstate")` code; instead call `inject(HISTORY_PORT_KEY).on_popstate(self._refresh_path, self.__mode__)`; store the returned handle
- [ ] 9.2 Rewrite `Location._refresh_path` — replace direct `context.window.location` and `context.window.history.state` access with `inject(HISTORY_PORT_KEY).current_path(self.__mode__)` and `inject(HISTORY_PORT_KEY).state(self.__mode__)`
- [ ] 9.3 Rewrite `Location.destroy` — replace direct `context.window.removeEventListener` and `.destroy()` with `inject(HISTORY_PORT_KEY).off_popstate(self._popstate_handle, self.__mode__)`
- [ ] 9.4 Remove unused imports from `Location` (`inject`, `InjectionError`, `pyscript.context`, `pyscript.ffi`)

## 10. Router — accept Location via constructor

- [ ] 10.1 Change `Router.__init__` signature to accept `location: Location` as a required parameter
- [ ] 10.2 Remove internal `self._location = Location(...)` from `Router.__init__`
- [ ] 10.3 Update all callers of `Router(...)` — `WebComPyApp.__init__`, E2E test apps (`my_app/router.py`)

## 11. RouterLink — navigate via HistoryPort

- [ ] 11.1 Replace `ENVIRONMENT != "pyscript"` guard + `context.window.history.pushState` + `context.window.location` access in `_on_click` with `inject(HISTORY_PORT_KEY).navigate(href, state, self._router.__mode__)` and `inject(HISTORY_PORT_KEY).current_path(self._router.__mode__)`
- [ ] 11.2 Remove unused imports (`context`, `ENVIRONMENT` if no longer needed) from `_link.py`

## 12. Migrate element system

- [x] 12.1 Migrate `webcompy/elements/types/_element.py` — replace `from webcompy._browser._modules import browser` with `inject(DOM_PORT_KEY)` and `inject(FFI_PORT_KEY)` for DOM operations and event proxy creation/destruction
- [x] 12.2 Migrate `webcompy/elements/types/_text.py` — use `dom_port.create_text_node()` and `dom_port.create_element("br")`, remove Pattern A `else: raise WebComPyException` guards; keep `_update_text()` server branch (Pattern B)
- [x] 12.3 Migrate `webcompy/elements/types/_abstract.py` — use `dom_port.create_text_node("")` for placeholder node creation in `_detach_node`; wrap raw JS nodes in `BrowserDOMNode` during `_get_existing_node`
- [x] 12.4 Migrate `webcompy/elements/types/_switch.py` — use `dom_port.schedule_macro_task()` instead of `browser.window.setTimeout`, replace `browser is not None` with `ENVIRONMENT == "pyscript"`
- [x] 12.5 Migrate `webcompy/elements/types/_repeat.py` — use `ENVIRONMENT` for `browser` truthiness checks
- [x] 12.6 Migrate `webcompy/elements/types/_dynamic.py` — remove `browser` import, use `ENVIRONMENT`

## 13. Migrate app, components, signal, aio, logging

- [x] 13.1 Migrate `webcompy/app/_root_component.py` — use `dom_port.query_selector()`, `dom_port.get_element_by_id()`, `dom_port.set_title()` instead of `browser.document.*`
- [x] 13.2 Migrate `webcompy/app/_app.py` — port providing done in task 7.4; update `_emit_profile_summary` to use `ENVIRONMENT` + `pyscript.context` instead of `browser`
- [x] 13.3 Migrate `webcompy/components/_component.py` — remove `browser` import, use `ENVIRONMENT`
- [x] 13.4 Migrate `webcompy/signal/_effect.py` — use `inject(DOM_PORT_KEY).schedule_macro_task()` instead of `browser.window.setTimeout()`
- [x] 13.5 Migrate `webcompy/aio/_aio.py` — remove `browser` import, use `ENVIRONMENT`
- [x] 13.6 Migrate `webcompy/logging.py` — use `pyscript.context.window.console` directly instead of `browser.console`

## 14. Migrate ajax (HttpClient → FetchPort)

- [x] 14.1 Move `Response` class and `WebComPyHttpClientException` to `webcompy/ports/_fetch.py`
- [x] 14.2 Move browser-specific fetch logic into `BrowserFetchPort.request()`
- [x] 14.3 Move server-side fetch logic into `ServerFetchPort.request()` via `httpx`
- [x] 14.4 Refactor `HttpClient` classmethods to delegate to `inject(FETCH_PORT_KEY).request()`
- [x] 14.5 Update `webcompy/ajax/__init__.py` to re-export from `webcompy/ports/_fetch.py`

## 15. Remove browser object entirely

- [x] 15.1 Delete `webcompy/_browser/` directory and all contents
- [x] 15.2 Remove `browser` from `webcompy/__init__.py` imports and `__all__`
- [x] 15.3 Update `pyproject.toml` stubPath from `webcompy/_browser` to `webcompy/ports`

## 16. Tests

- [x] 16.1 Update `tests/conftest.py` — remove `FakeBrowserModule`, add `FakeDOMNode`/`FakeDOMEvent`, add `browser_env` fixture with mock DOMPort/FFIPort/HistoryPort and DI scope
- [x] 16.2 Update `tests/test_base_elements.py`, `tests/test_elements_browser.py`, etc. to use `browser_env` fixture instead of monkeypatching `browser`
- [x] 16.3 Run existing unit test suite and fix regressions
- [ ] 16.4 Rewrite `tests/e2e/my_app/router.py` — pass `Location` to `Router(location=location, ...)`
- [ ] 16.5 Run full E2E test suite and fix regressions

## 17. Verification

- [x] 17.1 Run lint: `uv run ruff check .`
- [x] 17.2 Run type check: `uv run pyright`
- [x] 17.3 Run unit tests: `uv run python -m pytest tests/ --tb=short`
- [ ] 17.4 Run E2E tests (all groups, static + prod serving modes)
