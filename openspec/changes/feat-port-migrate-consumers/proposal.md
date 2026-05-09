## Why

Five files across `ajax/`, `aio/`, `signal/`, `logging.py`, and `components/_component.py` import the `browser` object directly. With `feat-port-definitions` and `feat-port-migrate-elements` complete, the remaining non-element consumers are migrated to port injection.

## What Changes

- **MODIFIED** `ajax/_fetch.py`: `browser.pyscript.fetch` → `inject(FETCH_PORT_KEY)`
- **MODIFIED** `aio/_aio.py`: `browser` truthiness → `ENVIRONMENT == "pyscript"`
- **MODIFIED** `signal/_effect.py`: `browser.window.setTimeout` → `inject(DOM_PORT_KEY).schedule_macro_task`
- **MODIFIED** `logging.py`: `browser.console` → `pyscript.context.window.console` (full method set: debug, info, warn, error)
- **MODIFIED** `router/_lazy.py`: `browser.console.warn` → `pyscript.context.window.console.warn`
- **MODIFIED** `components/_component.py`: `browser` truthiness → `ENVIRONMENT == "pyscript"`

## Capabilities

### Modified Capabilities

- `browser-api`: ajax, aio, signal, logging, and components subsystems migrated to port injection

## Non-goals

- Removing the `browser` object (subsequent phase)
- Changing the Router or Location API (subsequent phase)

## Impact

- **Affected**: ajax (1), aio (1), signal (1), logging (1), router/_lazy (1), components (1)
- **No breaking changes**: Migration is equivalent replacement only
