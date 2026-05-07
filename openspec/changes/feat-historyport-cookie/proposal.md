## Why

`Location` and `HistoryPort` have overlapping responsibilities (both manage reactive path state and navigation operations). Merge `Location` into `HistoryPort` and update `Router` to accept `HistoryPort` via constructor injection. Also add `CookiePort` browser/server implementations.

## What Changes

- **REMOVED** `Location` class — all functionality merged into `HistoryPort`
- **MODIFIED** `Router`: accepts `history: HistoryPort` via constructor instead of `location: Location`. **BREAKING**
- **MODIFIED** `RouterLink._on_click`: uses `inject(HISTORY_PORT_KEY).navigate()`
- **MODIFIED** `WebComPyApp`: also provides `CookiePort` in DI scope
- **REMOVED** `webcompy/router/_browser_history.py`, `_server_history.py`, `_history_port.py` (old HistoryPort definitions)
- **NEW** `BrowserCookiePort`, `ServerCookiePort` (already added by feat-port-definitions; this phase only provides them)

## Capabilities

### Modified Capabilities

- `router`: Router receives HistoryPort instead of Location. Breaking API change.
- `browser-api`: Location class removed, merged into HistoryPort.

## Impact

- **Breaking**: All `Router(...)` call sites must be updated
- **Breaking**: All `Location` references must be replaced with `HistoryPort`
- **Affected**: router/ (4 files), app/_app.py, E2E test apps
