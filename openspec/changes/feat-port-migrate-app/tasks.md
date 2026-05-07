## 1. Update _app.py

- [ ] 1.1 Add port key imports to `webcompy/app/_app.py` (`DOM_PORT_KEY`, `FFI_PORT_KEY`, `FETCH_PORT_KEY` from `webcompy.ports._keys`)
- [ ] 1.2 Import `BrowserDOMPort`, `BrowserFFIPort`, `BrowserFetchPort`, `BrowserHistoryPort` and provide them in PyScript branch. `BrowserHistoryPort` SHALL be constructed with `mode="hash"` (default constructor value)
- [ ] 1.3 Import `ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerHistoryPort` and provide them in server branch. `ServerHistoryPort` SHALL be constructed with `mode="hash"` (default constructor value)

## 2. Verification

- [ ] 2.1 Run lint and typecheck
- [ ] 2.2 Run all unit tests
- [ ] 2.3 Run full E2E suite
