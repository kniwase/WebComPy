## 1. Update _app.py

- [x] 1.1 Add `HISTORY_PORT_KEY` import to `webcompy/app/_app.py` (from `webcompy.ports._keys`)
- [x] 1.2 In the PyScript branch: import `BrowserHistoryPort` and provide it via `self._di_scope.provide(HISTORY_PORT_KEY, BrowserHistoryPort(mode="hash"))`
- [x] 1.3 In the server branch: import `ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerHistoryPort` and provide all four into `self._di_scope`
- [x] 1.4 Replace `from webcompy._browser._modules import browser as _browser` in `_emit_profile_summary` with `from pyscript import context` and replace `_browser.console.log(output)` with `context.window.console.log(output)`

## 2. Migrate _root_component.py

- [x] 2.1 Replace `from webcompy._browser._modules import browser` with DI key imports (`DOM_PORT_KEY`, `HEAD_PROPS_KEY`, `ROUTER_KEY`) and `ENVIRONMENT`
- [x] 2.2 Replace all `if browser:` guards with `if ENVIRONMENT == "pyscript":`
- [x] 2.3 Replace `browser.document.title = title` with `inject(DOM_PORT_KEY).set_title(title)`
- [x] 2.4 Replace `browser.document.documentElement.setAttribute(key, ...)` / `getAttribute(key)` / `removeAttribute(key)` by getting the root element via `inject(DOM_PORT_KEY).query_selector("html")` and calling `node.setAttribute(key, ...)` / `node.getAttribute(key)` / `node.removeAttribute(key)` on the returned `DOMNode`
- [x] 2.5 Replace `browser.document.querySelector(selector)` / `getElementById(...)` / `createElement(...)` with `inject(DOM_PORT_KEY).query_selector(...)` / `get_element_by_id(...)` / `create_element(...)`
- [x] 2.6 Replace `isinstance(value, Computed) and browser:` with `isinstance(value, Computed) and ENVIRONMENT == "pyscript":`
- [x] 2.7 Replace `not browser:` with `ENVIRONMENT != "pyscript":`
- [x] 2.8 Remove raw `browser` import

## 3. Verification

- [x] 3.1 Run lint and typecheck
- [x] 3.2 Run all unit tests
- [x] 3.3 Run full E2E suite (core E2E pass; docs E2E failures pre-existing)
