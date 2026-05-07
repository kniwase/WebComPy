## Why

Port implementations exist and all consumers can now use `inject(PORT_KEY)`. `WebComPyApp.__init__` must provide the ports into the DI scope so they are available at application startup.

## What Changes

- **MODIFIED** `webcompy/app/_app.py`: After `_register_deferred_components()`, provide the 4 port implementations (DOM, FFI, Fetch, History) into `self._di_scope.provide()` depending on environment

## Capabilities

### Modified Capabilities

- `app-config`: `WebComPyApp` bootstrap provides environment-specific ports into the DI scope

## Impact

- **Affected**: `webcompy/app/_app.py` only
- **No breaking changes**: All existing tests pass unchanged. Ports are already available; the app just starts providing them.
