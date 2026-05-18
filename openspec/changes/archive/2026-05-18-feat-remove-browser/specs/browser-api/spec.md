## ADDED Requirements

### Requirement: HostPort provides window-level operations
A `HostPort` SHALL provide the `schedule_macro_task` and `create_js_global_getter` methods for window-level operations, separate from `DOMPort`'s document-level operations.

#### Scenario: schedule_macro_task deferred via HostPort
- **WHEN** framework code calls `host_port.schedule_macro_task(callback)`
- **THEN** in the browser, the callback SHALL be deferred via `window.setTimeout(callback, 0)`
- **AND** in the server, the call SHALL be a no-op

#### Scenario: create_js_global_getter resolves window globals
- **WHEN** `create_js_global_getter("hljs")` is called in the browser
- **THEN** the returned zero-arg function SHALL return `window.hljs`
- **AND** if `wrapper` is provided, the wrapper function SHALL transform the resolved value
- **AND** if the global is missing, the result SHALL be `None` (or `default`, if provided)

#### Scenario: create_js_global_getter returns default on server
- **WHEN** `create_js_global_getter("hljs")` is called on the server (SSG)
- **THEN** the returned zero-arg function SHALL return `None` (or `default`, if provided)

#### Scenario: DOMPort no longer carries schedule_macro_task
- **WHEN** code inspects `DOMPort` ABC
- **THEN** `schedule_macro_task` SHALL NOT be present

### MODIFIED Requirements

### Requirement: browser public export removed
The `browser` public export from `webcomppy` SHALL be removed. The browser object definition SHALL be relocated to `webcompy/ports/_browser/_raw.py` as an internal implementation detail.

#### Scenario: public browser import raises AttributeError
- **WHEN** code attempts `from webcompy import browser`
- **THEN** Python SHALL raise `AttributeError`

#### Scenario: Internal browser object accessible for port implementations
- **WHEN** port implementations under `ports/_browser/` access the raw browser object
- **THEN** they SHALL import from `webcompy.ports._browser._raw`

#### Scenario: _browser/_modules.py preserved as re-export stub
- **WHEN** Router files (to be migrated in phase 6) import from `webcompy._browser._modules`
- **THEN** the import SHALL succeed via a thin re-export stub delegating to `webcompy.ports._browser._raw`
