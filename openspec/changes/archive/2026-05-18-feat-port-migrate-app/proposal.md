## Why

DOM, FFI, and Fetch ports are already provided into the DI scope by phase 3 (`feat-port-migrate-consumers`). This phase completes app-level port registration by adding `HistoryPort` in the browser branch and all four server-side port implementations. It also migrates `_root_component.py` from `browser` to port injection.

## What Changes

- **MODIFIED** `webcompy/app/_app.py`: Provide `BrowserHistoryPort` in the PyScript branch (alongside existing DOM/FFI/Fetch ports). Provide `ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerHistoryPort` in the server branch (preparatory for `feat-virtual-dom`)
- **MODIFIED** `webcompy/app/_root_component.py`: Replace `browser` imports and `if browser:` guards with port injection and `ENVIRONMENT` checks

## Capabilities

### Modified Capabilities

- `app-config`: `WebComPyApp` bootstrap provides `HistoryPort` (browser) and all server-side port implementations into the DI scope

## Non-goals

- Removing existing `browser` imports (next phase)
- Changing the Router API (subsequent phase)
- Providing `CookiePort` (phase 6)

## Impact

- **Affected**: `webcompy/app/_app.py`, `webcompy/app/_root_component.py`
- **No breaking changes**: All existing tests pass unchanged
