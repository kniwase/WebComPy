## 1. Relocate browser object to internal location

- [x] 1.1 Read the full contents of `webcompy/_browser/_modules.py` (browser object definition)
- [x] 1.2 Create `webcompy/ports/_browser/_raw.py` with the identical browser object definition (relocated from `_browser/_modules.py`)

## 2. Update port implementation imports

- [x] 2.1 Update `webcompy/ports/_browser/_dom.py`: `from webcompy._browser._modules import browser as _raw_browser` → `from webcompy.ports._browser._raw import browser as _raw_browser`
- [x] 2.2 Update `webcompy/ports/_browser/_ffi.py`: same import path change
- [x] 2.3 Update `webcompy/ports/_browser/_fetch.py`: same import path change
- [x] 2.4 Update `webcompy/ports/_browser/_history.py`: same import path change
- [x] 2.5 Update `webcompy/ports/_browser/_cookie.py`: same import path change
- [x] 2.6 Update `webcompy/ajax/_fetch.py`: FormData fallback import at line 111, same path change

## 3. Replace _browser/_modules.py with re-export stub

- [x] 3.1 Replace `webcompy/_browser/_modules.py` content with `from webcompy.ports._browser._raw import browser` (thin re-export stub for Router compatibility until phase 6)

## 4. Remove public browser export

- [x] 4.1 Remove `from webcompy._browser._modules import browser` line from `webcompy/_browser/__init__.py`
- [x] 4.2 Remove `browser` export from `webcompy/__init__.py`

## 5. Update configuration

- [x] 5.1 Update `pyproject.toml` stubPath: `webcompy/_browser` → `webcompy/ports`
- [x] 5.2 Remove `webcompy/_browser/_modules.pyi` stub file (ports provide type checking)

## 6. Fix docs_app browser consumers

- [x] 6.1 Fix `docs_app/components/navigation.py`: migrate to `DOM_PORT_KEY` injection with `add_document_event_listener` / `remove_document_event_listener`
- [x] 6.2 Fix `docs_app/components/syntax_highlighting.py`: change `from webcompy import browser` to `from webcompy.ports._browser._raw import browser`
- [x] 6.3 Fix `docs_app/components/demo_display.py`: change `from webcompy import browser` to `from webcompy.ports._browser._raw import browser`

## 7. Verify no remaining old-style imports

- [x] 7.1 Run `grep -rn "from webcompy\._browser\._modules import browser" webcompy/ --include="*.py"` — confirm zero matches outside `_browser/_modules.py` itself and Router files (which will be addressed in phase 6)
- [x] 7.2 Verify all port implementation files import from `webcompy.ports._browser._raw`
- [x] 7.3 Run `grep -rn "from webcompy import browser\|from webcompy\._browser import browser" docs_app/ tests/ --include="*.py"` — confirm zero matches for broken public browser imports

## 8. Verification

- [x] 8.1 Run lint and typecheck
- [x] 8.2 Run all unit tests (865 passed)
- [x] 8.3 Run full E2E suite (64 passed, 10 flaky — PyScript init timing, unrelated to changes)

## 9. Introduce HostPort

- [ ] 9.1 Create `webcompy/ports/_host.py` with `HostPort` ABC (schedule_macro_task, create_js_global_getter)
- [ ] 9.2 Create `webcompy/ports/_browser/_host.py` with `BrowserHostPort`
- [ ] 9.3 Create `webcompy/ports/_server/_host.py` with `ServerHostPort` (always returns default/None)
- [ ] 9.4 Add `HOST_PORT_KEY` to `webcompy/ports/_keys.py`

## 10. Migrate schedule_macro_task from DOMPort to HostPort

- [ ] 10.1 Remove `schedule_macro_task` from `DOMPort` ABC (`webcompy/ports/_dom.py`)
- [ ] 10.2 Remove `schedule_macro_task` from `BrowserDOMPort` (`webcompy/ports/_browser/_dom.py`)
- [ ] 10.3 Remove `schedule_macro_task` from `ServerDOMPort` (`webcompy/ports/_server/_dom.py`)
- [ ] 10.4 Remove `schedule_macro_task` from `FakeBrowserDOMPort` (`tests/conftest.py`)
- [ ] 10.5 Add `FakeBrowserHostPort` to `tests/conftest.py` with `schedule_macro_task` (no-op) and `create_js_global_getter` (returns default)
- [ ] 10.6 Update `webcompy/signal/_effect.py:146` — `inject(DOM_PORT_KEY)` → `inject(HOST_PORT_KEY)`
- [ ] 10.7 Update `webcompy/elements/types/_switch.py:82` — `inject(DOM_PORT_KEY)` → `inject(HOST_PORT_KEY)`

## 11. Provide HostPort in app bootstrap

- [ ] 11.1 Provide `BrowserHostPort` in `webcompy/app/_app.py` PyScript branch
- [ ] 11.2 Provide `ServerHostPort` in `webcompy/app/_app.py` server branch
- [ ] 11.3 Update `tests/conftest.py` `fake_browser_full` fixture to provide `FakeBrowserHostPort`

## 12. Migrate docs_app hljs consumers from _raw to HostPort

- [ ] 12.1 Migrate `docs_app/components/syntax_highlighting.py`: `from webcompy.ports._browser._raw import browser` → inject-based `HOST_PORT_KEY` with `create_js_global_getter("hljs")`
- [ ] 12.2 Migrate `docs_app/components/demo_display.py`: `from webcompy.ports._browser._raw import browser` → inject-based `HOST_PORT_KEY` with `create_js_global_getter("hljs")`

## 13. Verification

- [ ] 13.1 Run lint and typecheck
- [ ] 13.2 Run all unit tests
- [ ] 13.3 Run full E2E suite
