## Why

Port implementations exist and all consumers can now use `inject(PORT_KEY)`. `WebComPyApp.__init__` must provide the ports into the DI scope so they are available at application startup.

## What Changes

- **MODIFIED** `webcompy/app/_app.py`: After `_register_deferred_components()`, provide the 4 port implementations (DOM, FFI, Fetch, History) into `self._di_scope.provide()` depending on environment
- **MODIFIED** `webcompy/app/_root_component.py`: Replace `browser` imports and `if browser:` guards with `inject(PORT_KEY)` calls and `ENVIRONMENT == "pyscript"` checks

## Capabilities

### Modified Capabilities

- `app-config`: `WebComPyApp` bootstrap provides environment-specific ports into the DI scope

## Non-goals

- Removing existing `browser` imports (next phase)
- Changing the Router API (subsequent phase)
- Providing `CookiePort` (phase 6)

## Impact

- **Affected**: `webcompy/app/_app.py`, `webcompy/app/_root_component.py`
- **No breaking changes**: All existing tests pass unchanged. Ports are already available; the app just starts providing them.
