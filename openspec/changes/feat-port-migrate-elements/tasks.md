## 1. Migrate _element.py

- [x] 1.1 Replace `from webcompy._browser._modules import browser` with `from webcompy.di import inject` and `from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY` and `from webcompy.utils import ENVIRONMENT`
- [x] 1.2 Replace `if browser: return browser.pyscript.ffi.create_proxy(handler) else: return handler` in `_generate_event_handler` with `if ENVIRONMENT == "pyscript": return inject(FFI_PORT_KEY).create_proxy(handler); return handler`
- [x] 1.3 Replace `if browser:` guard in `_init_node` with `if ENVIRONMENT == "pyscript":`; replace `browser.document.createElement` with `inject(DOM_PORT_KEY).create_element`
- [x] 1.4 Replace `if browser:` guard and `browser.document` calls in `_create_node`
- [x] 1.5 Replace `if browser: handler.destroy()` in `_detach_from_node` with `if ENVIRONMENT == "pyscript": handler.destroy()`
- [x] 1.6 Replace `if browser: event_handler.destroy()` in `_remove_element` with `if ENVIRONMENT == "pyscript": event_handler.destroy()`

## 2. Migrate _text.py

- [x] 2.1 Replace `browser` import with DI keys and `ENVIRONMENT`
- [x] 2.2 Replace `if browser:` + `browser.document.*` calls in `_init_node` and `_create_node` methods of both `NewLine` and `TextElement`
- [x] 2.3 Replace `if browser:` guard in `_update_text` with `if ENVIRONMENT == "pyscript":`

## 3. Migrate _abstract.py

- [x] 3.1 Replace `browser` import with `inject` and `DOM_PORT_KEY` and `ENVIRONMENT`
- [x] 3.2 Replace `if browser and self._node_cache:` in `_detach_node` with `if ENVIRONMENT == "pyscript" and self._node_cache:`
- [x] 3.3 Replace `browser.document.createTextNode` with `inject(DOM_PORT_KEY).create_text_node`

## 4. Migrate _switch.py

- [x] 4.1 Replace `browser` import with `inject`, `DOM_PORT_KEY`, `ENVIRONMENT`
- [x] 4.2 Replace `browser is not None` checks with `ENVIRONMENT == "pyscript"`
- [x] 4.3 Replace `browser.window.setTimeout(cb, 0)` with `inject(DOM_PORT_KEY).schedule_macro_task(cb)`
- [x] 4.4 Replace `if not browser:` with `if ENVIRONMENT != "pyscript":`

## 5. Migrate _dynamic.py and _repeat.py

- [x] 5.1 Replace `browser` import with `ENVIRONMENT` in `_dynamic.py`
- [x] 5.2 Replace `if browser:` with `if ENVIRONMENT == "pyscript":` in `_dynamic._render`
- [x] 5.3 Replace `browser` import with `ENVIRONMENT` in `_repeat.py`
- [x] 5.4 Replace `if not browser:` with `if ENVIRONMENT != "pyscript":` in `_repeat._on_set_parent`
- [x] 5.5 Replace `browser` check in `_repeat._update_dom_range` with `ENVIRONMENT == "pyscript"`

## 6. Verification

- [x] 6.1 Run lint and typecheck
- [x] 6.2 Run all unit tests
- [x] 6.3 Run full E2E suite
