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
- [ ] 4.2 Replace `_browser.console.log` with `context.window.console.log`

## 5. Migrate components

- [ ] 5.1 Replace `browser` import with `ENVIRONMENT` in `webcompy/components/_component.py`
- [ ] 5.2 Replace `browser` truthiness check with `ENVIRONMENT == "pyscript"`

## 6. Verification

- [ ] 6.1 Run lint and typecheck
- [ ] 6.2 Run all unit tests
- [ ] 6.3 Run full E2E suite
