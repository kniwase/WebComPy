## 1. Update _app.py

- [ ] 1.1 Add port key imports to `webcompy/app/_app.py` (`DOM_PORT_KEY`, `FFI_PORT_KEY`, `FETCH_PORT_KEY`, `HISTORY_PORT_KEY` from `webcompy.ports._keys`)
- [ ] 1.2 Import `BrowserDOMPort`, `BrowserFFIPort`, `BrowserFetchPort`, `BrowserHistoryPort` and provide them in PyScript branch. `BrowserHistoryPort` SHALL be constructed with `mode="hash"` (default constructor value)
- [ ] 1.3 Import `ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerHistoryPort` and provide them in server branch. `ServerHistoryPort` SHALL be constructed with `mode="hash"` (default constructor value)

## 2. Migrate _root_component.py

- [ ] 2.1 Replace `from webcompy._browser._modules import browser` with DI key imports (`DOM_PORT_KEY` only) and `ENVIRONMENT`
- [ ] 2.2 Replace all `if browser:` guards with `if ENVIRONMENT == "pyscript":`
- [ ] 2.3 Replace `browser.document.title = title` with `inject(DOM_PORT_KEY).set_title(title)`
- [ ] 2.4 Replace `browser.document.documentElement.setAttribute(key, ...)` / `getAttribute(key)` / `removeAttribute(key)` by getting the root element via `inject(DOM_PORT_KEY).query_selector("html")` and calling `node.setAttribute(key, ...)` / `node.getAttribute(key)` / `node.removeAttribute(key)` on the returned `DOMNode`
- [ ] 2.5 Replace `browser.document.querySelector(selector)` / `getElementById(...)` with `inject(DOM_PORT_KEY).query_selector(selector)` / `get_element_by_id(...)`
- [ ] 2.6 Replace `isinstance(value, Computed) and browser:` with `isinstance(value, Computed) and ENVIRONMENT == "pyscript":`
- [ ] 2.7 Replace `not browser:` with `ENVIRONMENT != "pyscript":`
- [ ] 2.8 Remove raw `browser` import

## 3. Verification

- [ ] 3.1 Run lint and typecheck
- [ ] 3.2 Run all unit tests
- [ ] 3.3 Run full E2E suite
