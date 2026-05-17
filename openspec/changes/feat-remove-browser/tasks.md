## 1. Relocate browser object to internal location

- [ ] 1.1 Read the full contents of `webcompy/_browser/_modules.py` (browser object definition)
- [ ] 1.2 Create `webcompy/ports/_browser/_raw.py` with the identical browser object definition (relocated from `_browser/_modules.py`)

## 2. Update port implementation imports

- [ ] 2.1 Update `webcompy/ports/_browser/_dom.py`: `from webcompy._browser._modules import browser as _raw_browser` → `from webcompy.ports._browser._raw import browser as _raw_browser`
- [ ] 2.2 Update `webcompy/ports/_browser/_ffi.py`: same import path change
- [ ] 2.3 Update `webcompy/ports/_browser/_fetch.py`: same import path change
- [ ] 2.4 Update `webcompy/ports/_browser/_history.py`: same import path change
- [ ] 2.5 Update `webcompy/ports/_browser/_cookie.py`: same import path change
- [ ] 2.6 Update `webcompy/ajax/_fetch.py`: FormData fallback import at line 111, same path change

## 3. Replace _browser/_modules.py with re-export stub

- [ ] 3.1 Replace `webcompy/_browser/_modules.py` content with `from webcompy.ports._browser._raw import browser` (thin re-export stub for Router compatibility until phase 6)

## 4. Remove public browser export

- [ ] 4.1 Remove `from webcompy._browser._modules import browser` line from `webcompy/_browser/__init__.py`
- [ ] 4.2 Remove `browser` export from `webcompy/__init__.py`

## 5. Update configuration

- [ ] 5.1 Update `pyproject.toml` stubPath: `webcompy/_browser` → `webcompy/ports`
- [ ] 5.2 Remove `webcompy/_browser/_modules.pyi` stub file (ports provide type checking)

## 6. Verify no remaining old-style imports

- [ ] 6.1 Run `grep -rn "from webcompy\._browser\._modules import browser" webcompy/ --include="*.py"` — confirm zero matches outside `_browser/_modules.py` itself and Router files (which will be addressed in phase 6)
- [ ] 6.2 Verify all port implementation files import from `webcompy.ports._browser._raw`

## 7. Verification

- [ ] 7.1 Run lint and typecheck
- [ ] 7.2 Run all unit tests
- [ ] 7.3 Run full E2E suite
