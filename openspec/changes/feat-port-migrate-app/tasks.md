## 1. Update _app.py

- [ ] 1.1 Add `HISTORY_PORT_KEY` import to `webcompy/app/_app.py` (from `webcompy.ports._keys`)
- [ ] 1.2 In the PyScript branch: import `BrowserHistoryPort` and provide it via `self._di_scope.provide(HISTORY_PORT_KEY, BrowserHistoryPort(mode="hash"))`
- [ ] 1.3 In the server branch: import `ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerHistoryPort` and provide all four into `self._di_scope`
- [ ] 1.4 Replace `from webcompy._browser._modules import browser as _browser` in `_emit_profile_summary` with `from pyscript import context` and replace `_browser.console.log(output)` with `context.window.console.log(output)`

## 2. Migrate _root_component.py

- [ ] 2.1 Replace `from webcompy._browser._modules import browser` with DI key imports (`DOM_PORT_KEY`, `HEAD_PROPS_KEY`, `ROUTER_KEY`) and `ENVIRONMENT`
- [ ] 2.2 Replace all `if browser:` guards with `if ENVIRONMENT == "pyscript":`
- [ ] 2.3 Replace `browser.document.title = title` with `inject(DOM_PORT_KEY).set_title(title)`
- [ ] 2.4 Replace `browser.document.documentElement.setAttribute(key, ...)` / `getAttribute(key)` / `removeAttribute(key)` by getting the root element via `inject(DOM_PORT_KEY).query_selector("html")` and calling `node.setAttribute(key, ...)` / `node.getAttribute(key)` / `node.removeAttribute(key)` on the returned `DOMNode`
- [ ] 2.5 Replace `browser.document.querySelector(selector)` / `getElementById(...)` / `createElement(...)` with `inject(DOM_PORT_KEY).query_selector(...)` / `get_element_by_id(...)` / `create_element(...)`
- [ ] 2.6 Replace `isinstance(value, Computed) and browser:` with `isinstance(value, Computed) and ENVIRONMENT == "pyscript":`
- [ ] 2.7 Replace `not browser:` with `ENVIRONMENT != "pyscript":`
- [ ] 2.8 Remove raw `browser` import

## 3. Verification

- [ ] 3.1 Run lint and typecheck
- [ ] 3.2 Run all unit tests
- [ ] 3.3 Run full E2E suite
