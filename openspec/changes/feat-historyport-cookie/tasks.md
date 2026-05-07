## 1. Integrate Location into HistoryPort

- [ ] 1.1 Merge `Location.__set_path__`, `_refresh_path`, `set_mode`, `value`, `state` logic into `HistoryPort` / `BrowserHistoryPort` / `ServerHistoryPort`
- [ ] 1.2 Delete `Location` class. Rename `webcompy/router/_change_event_handler.py` to `_history_events.py` with `type Location = HistoryPort` (type alias only, not instantiable)
- [ ] 1.3 Delete old `webcompy/router/_history_port.py`, `_browser_history.py`, `_server_history.py`

## 2. Update Router and RouterView

- [ ] 2.1 Change `Router.__init__` from `Location` to `history: HistoryPort` parameter. Remove `mode=`/`base_url=` from Router
- [ ] 2.2 Replace `self._location.__set_path__` with `self._history.navigate()` in `Router.__set_path__`
- [ ] 2.3 Update `Router.__cases__` computed to track `self._history.value`
- [ ] 2.4 Update `RouterView._on_set_parent` to work with HistoryPort-aware Router
- [ ] 2.5 Remove `HISTORY_PORT_KEY` from `webcompy/router/_keys.py` (key is now in `webcompy/ports/_keys.py` from phase 1). Update all imports of `HISTORY_PORT_KEY` to use `webcompy.ports._keys`.

## 3. Update RouterLink

- [ ] 3.1 Replace `self._router.__set_path__(href, params)` with `inject(HISTORY_PORT_KEY).navigate(href, state)` in `_on_click`

## 4. Update WebComPyApp

- [ ] 4.1 Provide `CookiePort` in DI scope
- [ ] 4.2 Provide `HistoryPort` in DI scope before Router construction

## 5. Update public API exports

- [ ] 5.1 Update `webcompy/ports/__init__.py` — export all ABCs, `DOMNodeList`, DI keys
- [ ] 5.2 Remove `Location` exports from `webcompy/router/__init__.py`

## 6. Update tests and E2E apps

- [ ] 6.1 Add `MockHistoryPort` (inherits `HistoryPort`) to `tests/conftest.py`
- [ ] 6.2 Update all `Router(mode=...)` calls in unit tests, conftest fixtures, E2E apps
- [ ] 6.3 Update `test_location.py` to test `BrowserHistoryPort` instead of `Location`
- [ ] 6.4 Update E2E my_app/router.py to use new Router API

## 7. Verification

- [ ] 7.1 Run lint and typecheck
- [ ] 7.2 Run all unit tests
- [ ] 7.3 Run full E2E suite
