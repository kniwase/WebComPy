## 1. Migrate ajax

- [x] 1.1 Replace `browser.pyscript.fetch` with `inject(FETCH_PORT_KEY).fetch` in `webcompy/ajax/_fetch.py`

## 2. Migrate aio

- [x] 2.1 Replace `browser` import with `ENVIRONMENT` in `webcompy/aio/_aio.py`
- [x] 2.2 Replace `browser` truthiness check with `ENVIRONMENT == "pyscript"`

## 3. Migrate signal/effect

- [x] 3.1 Remove `browser` try/import block from `webcompy/signal/_effect.py`
- [x] 3.2 Add imports for `inject`, `InjectionError`, `DOM_PORT_KEY`
- [x] 3.3 Replace `browser.window.setTimeout(cb, 0)` with `inject(DOM_PORT_KEY).schedule_macro_task(cb)` with exception fallback

## 4. Migrate logging

- [x] 4.1 Replace `browser` import with `pyscript.context` import in `webcompy/logging.py`
- [x] 4.2 Replace `_browser.console` (used as `_handler`) with `context.window.console` (preserving full method set: debug, info, warn, error)

## 5. Migrate components

- [x] 5.1 Replace `browser` import with `ENVIRONMENT` in `webcompy/components/_component.py`
- [x] 5.2 Replace `browser` truthiness check with `ENVIRONMENT == "pyscript"`

## 6. Migrate router/_lazy

- [x] 6.1 Replace `browser` try/import block with `pyscript.context` import in `webcompy/router/_lazy.py`
- [x] 6.2 Replace `browser.console.warn(...)` with `context.window.console.warn(...)`

## 7. Verification

- [x] 7.1 Run lint and typecheck
- [x] 7.2 Run all unit tests
- [x] 7.3 Run full E2E suite
