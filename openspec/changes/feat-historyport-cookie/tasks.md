## 1. Integrate Location into HistoryPort

- [ ] 1.1 Merge `Location.__set_path__`, `_refresh_path`, `set_mode`, `value`, `state` logic into `HistoryPort` / `BrowserHistoryPort` / `ServerHistoryPort`
- [ ] 1.2 Delete `Location` class. Rename `webcompy/router/_change_event_handler.py` to `_history_events.py` with `type Location = HistoryPort` (type alias only, not instantiable)
- [ ] 1.3 Delete old HistoryPort duplicates (none exist — HistoryPort was defined in `webcompy/ports/_history.py` in phase 1)

## 2. Update Router

- [ ] 2.1 Change `Router.__init__` from `Location` to `history: HistoryPort` parameter. Remove `mode=`/`base_url=` from Router
- [ ] 2.2 Replace `self._location.__set_path__` with `self._history.navigate()` in `Router.__set_path__`
- [ ] 2.3 Update `Router.__cases__` computed to track `self._history.value`
- [ ] 2.4 Ensure no `HISTORY_PORT_KEY` exists in `webcompy/router/_keys.py` (key is defined in `webcompy/ports/_keys.py` from phase 1). Verify all consumers import `HISTORY_PORT_KEY` from `webcompy.ports._keys`.

## 3. Update RouterLink

- [ ] 3.1 Replace `from webcompy._browser._modules import browser` import with `from pyscript import context` and `ENVIRONMENT`
- [ ] 3.2 Replace `if not browser:` guard with `if ENVIRONMENT != "pyscript":`
- [ ] 3.3 Replace `browser.window.location.pathname` / `browser.window.location.hash` with `context.window.location.pathname` / `context.window.location.hash`
- [ ] 3.4 Replace `browser.window.history.pushState(state, None, href)` with `context.window.history.pushState(state, None, href)`
- [ ] 3.5 Replace `self._router.__set_path__(href, params)` with `inject(HISTORY_PORT_KEY).navigate(href, state)`

## 4. Update RouterView

- [ ] 4.1 Replace `from webcompy._browser._modules import browser` import with `ENVIRONMENT`
- [ ] 4.2 Replace `if not browser:` with `if ENVIRONMENT != "pyscript":`
- [ ] 4.3 Update `_on_set_parent` to work with HistoryPort-aware Router

## 5. Update Router preload_lazy_routes

- [ ] 5.1 Replace `from webcompy._browser._modules import browser` with `inject(DOM_PORT_KEY)` and `ENVIRONMENT`
- [ ] 5.2 Replace `if browser:` with `if ENVIRONMENT == "pyscript":`
- [ ] 5.3 Replace `browser.window.setTimeout(_batch_preload, 0)` with `inject(DOM_PORT_KEY).schedule_macro_task(_batch_preload)`

## 6. Update WebComPyApp

- [ ] 6.1 Provide `CookiePort` in DI scope
- [ ] 6.2 `HistoryPort` already provided in phase 4; verify it is available before `Router` construction

## 7. Update public API exports

- [ ] 7.1 Update `webcompy/ports/__init__.py` — export all ABCs, `DOMNodeList`, DI keys
- [ ] 7.2 Remove `Location` exports from `webcompy/router/__init__.py`

## 8. Remove _browser/ directory

- [ ] 8.1 Verify zero imports remaining: `grep -rn "from webcompy\._browser" webcompy/ tests/ --include="*.py"` confirms no matches
- [ ] 8.2 Delete `webcompy/_browser/_modules.py` (re-export stub from phase 5)
- [ ] 8.3 Delete `webcompy/_browser/__init__.py`
- [ ] 8.4 Delete `webcompy/_browser/` directory

## 9. Update tests and E2E apps

- [ ] 9.1 Add `MockHistoryPort` (inherits `HistoryPort`) to `tests/conftest.py`
- [ ] 9.2 Update all `Router(mode=...)` calls in unit tests, conftest fixtures, E2E apps
- [ ] 9.3 Update `test_location.py` to test `BrowserHistoryPort` instead of `Location`
- [ ] 9.4 Update E2E my_app/router.py to use new Router API

## 10. Verification

- [ ] 10.1 Run lint and typecheck
- [ ] 10.2 Run all unit tests
- [ ] 10.3 Run full E2E suite
