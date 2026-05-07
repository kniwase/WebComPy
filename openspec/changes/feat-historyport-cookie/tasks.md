## 1. Integrate Location into HistoryPort

- [ ] 1.1 Merge `Location.__set_path__`, `_refresh_path`, `set_mode`, `value`, `state` logic into `HistoryPort` / `BrowserHistoryPort` / `ServerHistoryPort`
- [ ] 1.2 Remove `Location` class and `webcompy/router/_change_event_handler.py` (or update alias)
- [ ] 1.3 Delete old `webcompy/router/_history_port.py`, `_browser_history.py`, `_server_history.py`

## 2. Update Router to use HistoryPort

- [ ] 2.1 Change `Router.__init__` from `Location` to `history: HistoryPort` parameter. Remove `mode=`/`base_url=` from Router
- [ ] 2.2 Replace `self._location.__set_path__` with `self._history.navigate()` in `Router.__set_path__`
- [ ] 2.3 Update `Router.__cases__` computed to track `self._history.value`
- [ ] 2.4 Move `HISTORY_PORT_KEY` from `webcompy/router/_keys.py` to `webcompy/ports/_keys.py`

## 3. Update RouterLink

- [ ] 3.1 Replace `self._router.__set_path__(href, params)` with `inject(HISTORY_PORT_KEY).navigate(href, state)` in `_on_click`

## 4. Update WebComPyApp

- [ ] 4.1 Provide `CookiePort` in DI scope
- [ ] 4.2 Provide `HistoryPort` in DI scope before Router construction

## 5. Update tests and E2E apps

- [ ] 5.1 Update all `Router(mode=...)` calls in unit tests, conftest fixtures, E2E apps
- [ ] 5.2 Update `test_location.py` to test `BrowserHistoryPort` instead of `Location`
- [ ] 5.3 Update E2E my_app/router.py to use new Router API

## 6. Verification

- [ ] 6.1 Run lint and typecheck
- [ ] 6.2 Run all unit tests
- [ ] 6.3 Run full E2E suite
