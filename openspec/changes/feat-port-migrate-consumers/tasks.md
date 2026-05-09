## 1. Migrate ajax

- [ ] 1.1 Replace `browser.pyscript.fetch` with `inject(FETCH_PORT_KEY).fetch` in `webcompy/ajax/_fetch.py`

## 2. Migrate aio

- [ ] 2.1 Replace `browser` import with `ENVIRONMENT` in `webcompy/aio/_aio.py`
- [ ] 2.2 Replace `browser` truthiness check with `ENVIRONMENT == "pyscript"`

## 3. Migrate signal/effect

- [ ] 3.1 Remove `browser` try/import block from `webcompy/signal/_effect.py`
- [ ] 3.2 Add imports for `inject`, `InjectionError`, `DOM_PORT_KEY`
- [ ] 3.3 Replace `browser.window.setTimeout(cb, 0)` with `inject(DOM_PORT_KEY).schedule_macro_task(cb)` with exception fallback

## 4. Migrate logging

- [ ] 4.1 Replace `browser` import with `pyscript.context` import in `webcompy/logging.py`
- [ ] 4.2 Replace `_browser.console` (used as `_handler`) with `context.window.console` (preserving full method set: debug, info, warn, error)

## 5. Migrate components

- [ ] 5.1 Replace `browser` import with `ENVIRONMENT` in `webcompy/components/_component.py`
- [ ] 5.2 Replace `browser` truthiness check with `ENVIRONMENT == "pyscript"`

## 6. Migrate router/_lazy

- [ ] 6.1 Replace `browser` try/import block with `pyscript.context` import in `webcompy/router/_lazy.py`
- [ ] 6.2 Replace `browser.console.warn(...)` with `context.window.console.warn(...)`

## 7. Verification

- [ ] 7.1 Run lint and typecheck
- [ ] 7.2 Run all unit tests
- [ ] 7.3 Run full E2E suite
