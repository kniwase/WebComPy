## Why

Six files in `webcompy/elements/` import the `browser` object for DOM operations and event proxy creation. With `feat-port-definitions` complete, the port ABCs and implementations are available as dead code. This phase migrates only the element system to port injection, replacing `browser` guards with equivalent `ENVIRONMENT == "pyscript"` guards while preserving all server-side code paths.

## What Changes

- **MODIFIED** `_element.py`: `browser` → `inject(FFI_PORT_KEY)` and `inject(DOM_PORT_KEY)`. `if browser:` → `if ENVIRONMENT == "pyscript":`
- **MODIFIED** `_text.py`: `browser` → `inject(DOM_PORT_KEY)`
- **MODIFIED** `_abstract.py`: `browser` → `inject(DOM_PORT_KEY)`
- **MODIFIED** `_switch.py`: `browser.window.setTimeout` → `inject(DOM_PORT_KEY).schedule_macro_task`
- **MODIFIED** `_dynamic.py`: `if browser:` → `if ENVIRONMENT == "pyscript":`
- **MODIFIED** `_repeat.py`: `if browser`/`not browser` → `ENVIRONMENT` checks

## Capabilities

### Modified Capabilities

- `browser-api`: Six element files migrated to port injection. All browser API access through `inject(DOM_PORT_KEY)`/`inject(FFI_PORT_KEY)`. `browser` import replaced by `ENVIRONMENT` checks. Server-side fallback paths preserved.

## Impact

- **Affected**: 6 files in `webcompy/elements/types/`
- **No breaking changes**: All existing tests pass unchanged
- **Dependencies**: `feat-port-definitions` must be implemented first
