## 1. Package scaffolding

- [x] 1.1 Create `webcompy/ports/` package structure with `__init__.py` and sub-package directories (`_browser/`, `_server/`)
- [x] 1.2 Add `httpx` as production dependency via `uv add httpx`

## 2. DOMNode ABC

- [ ] 2.1 Rewrite `DOMNode` from Protocol to ABC in `webcompy/ports/_dom.py` — explicit methods: `appendChild`, `insertBefore`, `replaceChild`, `removeChild`, `remove`, `setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`, `addEventListener` (with `capture=False`), `removeEventListener`, `textContent` (property), `nodeName` (property), `nodeType` (property), `childNodes`, `__webcompy_node__` (property with setter)
- [ ] 2.2 Define `DOMNodeList` class (not ABC) with `length: int` property and `__getitem__(index: int) -> DOMNode`
- [ ] 2.3 Define `DOMPort` ABC in `webcompy/ports/_dom.py` with abstract methods: `create_element`, `create_text_node`, `query_selector`, `get_element_by_id`, `set_title`, `schedule_macro_task`
- [ ] 2.4 Update `BrowserDOMNode` in `webcompy/ports/_browser/_dom.py` to inherit from `DOMNode`
- [ ] 2.5 Update `BrowserDOMPort` in `webcompy/ports/_browser/_dom.py` to inherit from `DOMPort`
- [ ] 2.6 Update `ServerDOMPort` in `webcompy/ports/_server/_dom.py` to inherit from `DOMPort`

## 3. FFIPort ABC and implementations

- [ ] 3.1 Rewrite `FFIPort` from Protocol to ABC in `webcompy/ports/_ffi.py` with abstract methods: `create_proxy`, `destroy_proxy`, `is_none`, `to_js`, `assign`
- [ ] 3.2 Update `BrowserFFIPort` to inherit from `FFIPort`
- [ ] 3.3 Update `ServerFFIPort` to inherit from `FFIPort`

## 4. FetchPort ABC and implementations

- [ ] 4.1 Rewrite `FetchPort` from Protocol to ABC in `webcompy/ports/_fetch.py`
- [ ] 4.2 Update `BrowserFetchPort` to inherit from `FetchPort`
- [ ] 4.3 Update `ServerFetchPort` to inherit from `FetchPort`

## 5. CookiePort ABC and implementations (NEW)

- [ ] 5.1 Define `CookiePort` ABC in `webcompy/ports/_cookie.py`: `get(name)`, `set(name, value, *, max_age, path, secure, httponly, samesite)`, `delete(name, path)`, `get_all()`
- [ ] 5.2 Implement `BrowserCookiePort` in `webcompy/ports/_browser/_cookie.py` — delegates to `document.cookie`
- [ ] 5.3 Implement `ServerCookiePort` in `webcompy/ports/_server/_cookie.py` — parses `Cookie` header, accumulates `Set-Cookie`

## 6. HistoryPort ABC — merge Location into it

- [ ] 6.1 Define `HistoryPort` ABC in `webcompy/ports/_history.py` — extends `SignalBase[str]`, adds abstract: `current_search`, `history_state` (properties), `navigate(url, state=None)`, `refresh_from_window()` (internal hook called by browser impl on popstate)
- [ ] 6.2 Implement `BrowserHistoryPort` in `webcompy/ports/_browser/_history.py` — extends `HistoryPort`; `navigate` calls `pushState` then updates `self.value`; constructor registers popstate listener via `pyscript.ffi`; popstate callback calls `refresh_from_window`
- [ ] 6.3 Implement `ServerHistoryPort` in `webcompy/ports/_server/_history.py` — extends `HistoryPort`; stores path internally; `navigate` sets `self.value`; popstate no-op
- [ ] 6.4 Delete old `webcompy/router/_history_port.py`, `_browser_history.py`, `_server_history.py`

## 7. DI keys

- [ ] 7.1 Update `webcompy/ports/_keys.py` — add `COOKIE_PORT_KEY`, move `HISTORY_PORT_KEY` from router
- [ ] 7.2 Remove `HISTORY_PORT_KEY` from `webcompy/router/_keys.py`
- [ ] 7.3 Add `HISTORY_PORT_KEY` import to `webcompy/ports/__init__.py`

## 8. Delete Location, update Router and RouterLink

- [ ] 8.1 Delete `Location` class from `webcompy/router/_change_event_handler.py` — rename file to `_history_events.py` or similar, remove all Location code
- [ ] 8.2 Update `Router` — replace `self._location: Location` with `self._history: HistoryPort`; constructor receives `history: HistoryPort` instead of creating Location internally
- [ ] 8.3 Update `RouterLink._on_click` — use `inject(HISTORY_PORT_KEY).navigate(href, state)`
- [ ] 8.4 Update `RouterView._on_set_parent` — use `HistoryPort`-aware logic
- [ ] 8.5 Update `WebComPyApp.__init__` — provide all ports, construct `HistoryPort` within DI scope, pass to `Router`

## 9. Update existing migrations (already done, now need ABC compatibility)

- [x] 9.1 Element system files use `inject(DOM_PORT_KEY)` / `inject(FFI_PORT_KEY)` (no change needed)
- [x] 9.2 App/component/signal/aio/logging files migrated (no change needed)
- [x] 9.3 Ajax migrated to `inject(FETCH_PORT_KEY)` (no change needed)
- [x] 9.4 `webcompy/_browser/` removed (already done)

## 10. Update public API

- [ ] 10.1 Update `webcompy/ports/__init__.py` — export `HistoryPort`, `CookiePort`, `COOKIE_PORT_KEY`
- [ ] 10.2 Remove `Location` exports from router `__init__.py`

## 11. Tests

- [ ] 11.1 Update `tests/conftest.py` — replace `FakeDOMNode` / `FakeDOMEvent` / `browser_env` with HistoryPort-aware fixtures; add `MockHistoryPort` inheriting from `HistoryPort`
- [ ] 11.2 Update unit tests for new Router API (pass `HistoryPort` instead of Location)
- [ ] 11.3 Fix E2E test apps (`my_app/router.py`) — pass `HistoryPort` to Router
- [ ] 11.4 Run unit tests: `uv run python -m pytest tests/ --tb=short -k "not (e2e or e2e_docs)"`
- [ ] 11.5 Run E2E tests: `uv run python -m pytest tests/e2e/ --tb=short --serving-mode=static`

## 12. Verification

- [ ] 12.1 Run lint: `uv run ruff check .`
- [ ] 12.2 Run type check: `uv run pyright`
- [ ] 12.3 Run unit tests (pass)
- [ ] 12.4 Run E2E tests (pass)
