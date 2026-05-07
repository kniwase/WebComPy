## 1. Package Structure and Dependencies

- [ ] 1.1 Add `httpx` to `pyproject.toml` dependencies
- [ ] 1.2 Create `webcompy/ports/__init__.py` (empty, marks package)
- [ ] 1.3 Create `webcompy/ports/_browser/__init__.py` (empty)
- [ ] 1.4 Create `webcompy/ports/_server/__init__.py` (empty)

## 2. DI Keys

- [ ] 2.1 Create `webcompy/ports/_keys.py` with `InjectKey` instances for DOM_PORT_KEY, FFI_PORT_KEY, FETCH_PORT_KEY, COOKIE_PORT_KEY, HISTORY_PORT_KEY

## 3. DOMPort and DOMNode

- [ ] 3.1 Create `webcompy/ports/_dom.py` with `DOMNode` ABC (tree, attr, event, content methods + WebComPy markers)
- [ ] 3.2 Create `webcompy/ports/_dom.py` with `DOMPort` ABC (create_element, create_text_node, query_selector, get_element_by_id, set_title, schedule_macro_task)
- [ ] 3.3 Create `webcompy/ports/_browser/_dom.py` with `BrowserDOMNode` subclass wrapping real DOM elements
- [ ] 3.4 Create `webcompy/ports/_browser/_dom.py` with `BrowserDOMPort` subclass using `pyscript.context.document`
- [ ] 3.5 Create `webcompy/ports/_server/_dom.py` with `ServerDOMNode` subclass using plain dict/class state
- [ ] 3.6 Create `webcompy/ports/_server/_dom.py` with `ServerDOMPort` subclass

## 4. FFIPort

- [ ] 4.1 Create `webcompy/ports/_ffi.py` with `FFIPort` ABC (create_proxy, destroy_proxy, is_none, to_js, assign)
- [ ] 4.2 Create `webcompy/ports/_browser/_ffi.py` with `BrowserFFIPort` subclass using `pyscript.ffi`
- [ ] 4.3 Create `webcompy/ports/_server/_ffi.py` with `ServerFFIPort` subclass (pass-through implementations)

## 5. FetchPort

- [ ] 5.1 Create `webcompy/ports/_fetch.py` with `Response` dataclass and `FetchPort` ABC
- [ ] 5.2 Create `webcompy/ports/_browser/_fetch.py` with `BrowserFetchPort` subclass using `pyscript.fetch`
- [ ] 5.3 Create `webcompy/ports/_server/_fetch.py` with `ServerFetchPort` subclass using `httpx`

## 6. CookiePort

- [ ] 6.1 Create `webcompy/ports/_cookie.py` with `CookiePort` ABC (get, set, delete)
- [ ] 6.2 Create `webcompy/ports/_browser/_cookie.py` with `BrowserCookiePort` subclass using `document.cookie`
- [ ] 6.3 Create `webcompy/ports/_server/_cookie.py` with `ServerCookiePort` subclass (dict-based)

## 7. HistoryPort

- [ ] 7.1 Create `webcompy/ports/_history.py` with `HistoryPort` ABC extending `SignalBase[str]` (concrete `value` property with `producer_accessed()`, abstract `current_search`, `history_state`, `navigate`)
- [ ] 7.2 Create `webcompy/ports/_browser/_history.py` with `BrowserHistoryPort` subclass (reads from `pyscript.context.window`, popstate listener, reactive navigate)
- [ ] 7.3 Create `webcompy/ports/_server/_history.py` with `ServerHistoryPort` subclass (internal path storage, reactive navigate)

## 8. Verification

- [ ] 8.1 Run `uv run ruff check .` and fix any lint issues
- [ ] 8.2 Run `uv run pyright` and fix any type errors
- [ ] 8.3 Run `uv run python -m pytest tests/ -k "not (e2e or e2e_docs)" --ignore=tests/test_config_discovery.py` — confirm all existing tests pass unchanged
- [ ] 8.4 Run full E2E suite to confirm zero regression
