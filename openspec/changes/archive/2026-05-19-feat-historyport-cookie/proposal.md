## Why

`Location` and `HistoryPort` have overlapping responsibilities (both manage reactive path state and navigation operations). Merge `Location` into `HistoryPort` and update `Router` to accept `HistoryPort` via constructor injection. Also add `CookiePort` browser/server implementations. Finally, complete `_browser/` directory removal since all Router `browser` references are migrated in this phase.

## What Changes

- **REMOVED** `Location` class — all functionality merged into `HistoryPort`
- **MODIFIED** `Router`: accepts `history: HistoryPort` via constructor instead of `location: Location`. **BREAKING**
- **MODIFIED** `RouterLink._on_click`: uses `inject(HISTORY_PORT_KEY).navigate()`
- **MODIFIED** `WebComPyApp`: also provides `CookiePort` in DI scope
- **REMOVED** `webcompy/_browser/_modules.py` (re-export stub, no longer needed after Router migration)
- **REMOVED** `webcompy/_browser/` directory entirely
- **NEW** `BrowserCookiePort`, `ServerCookiePort` (already defined in phase 1; this phase only provides them)

## Capabilities

### Modified Capabilities

- `router`: Router receives HistoryPort instead of Location. Breaking API change.
- `browser-api`: Location class removed, merged into HistoryPort. `_browser/` directory fully deleted.

## Known Issues Addressed

- **Location popstate proxy lifecycle**: The `Location` class required manual `destroy()` calls to clean up popstate proxy objects. By merging Location into `HistoryPort`/`BrowserHistoryPort`, the proxy lifecycle is managed internally — `BrowserHistoryPort.__init__` creates the proxy and `destroy()` releases it. Consumers no longer need to manage popstate cleanup.

## Non-goals

- Changing the Router mode or base_url API surface
- Adding new HistoryPort methods beyond what Location already provided

## Impact

- **Breaking**: All `Router(...)` call sites must be updated
- **Breaking**: All `Location` references must be replaced with `HistoryPort`
- **Breaking**: `_browser/` directory fully deleted; raw browser object only accessible via `ports/_browser/_raw.py` internally
- **Affected**: router/ (4 files), app/_app.py, E2E test apps
