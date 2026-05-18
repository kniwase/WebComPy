## ADDED Requirements

### Requirement: Port responsibilities are scoped by browser API surface
Ports SHALL be organized around distinct browser API surfaces rather than arbitrary groupings. `DOMPort` SHALL handle document-level operations (`document.createElement`, `document.querySelector`, `document.title`, `document.addEventListener`). `HostPort` SHALL handle general window-level operations (JS global object access via `window[name]`, `window.setTimeout` for macro-task scheduling). Additional port ABCs SHALL be introduced when a new category of browser API surface is identified, following MDN's classification of browser features. This ensures each port has a clear, narrow responsibility and prevents ports from becoming monolithic catch-all abstractions.

Existing ports already demonstrate this principle:
- `CookiePort` is an independent port for `document.cookie`, separate from `DOMPort`'s broader document operations.
- `HistoryPort` is an independent port for `window.location` and `window.history`, separate from `HostPort`'s general window operations.
- `FetchPort` is an independent port for the global `fetch()` API, which belongs to neither document nor window.
- `FFIPort` is an independent port for the PyScript/Emscripten Python-to-JS bridge — not a web platform API at all, but its own distinct concern.

#### Scenario: Document operations belong to DOMPort
- **WHEN** a framework operation interacts with `document` (element creation, selector queries, title, document event listeners)
- **THEN** it SHALL use `DOMPort`

#### Scenario: Window operations belong to HostPort
- **WHEN** a framework operation interacts with `window` (JS globals, `setTimeout`)
- **THEN** it SHALL use `HostPort`

#### Scenario: Specific document or window sub-APIs get their own ports
- **WHEN** a browser API surface under `document` or `window` has sufficient scope to warrant independent abstraction (e.g., `document.cookie` → `CookiePort`, `window.location` + `window.history` → `HistoryPort`)
- **THEN** a dedicated port SHALL be introduced for that sub-API
- **AND** the general port (`DOMPort` or `HostPort`) SHALL NOT absorb it

#### Scenario: APIs outside document/window get their own ports
- **WHEN** a browser API surface does not belong to `document` or `window` (e.g., `fetch()` → `FetchPort`, `navigator` in the future)
- **THEN** a dedicated port SHALL be introduced for that API surface

#### Scenario: Non-web-platform concerns get their own ports
- **WHEN** a concern is not a web platform API but a runtime bridge or tooling abstraction (e.g., PyScript/Emscripten FFI → `FFIPort`)
- **THEN** it MAY have its own dedicated port

#### Scenario: Scope creep is rejected
- **WHEN** a need arises for a browser API surface that does not fit an existing port's scope
- **THEN** a new port SHALL be introduced rather than extending an existing port
- **AND** the existing port ABCs SHALL NOT be extended with methods outside their scope
