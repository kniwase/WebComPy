## MODIFIED Requirements

### Requirement: AJAX accesses fetch via port
The `webcompy.ajax` module SHALL obtain HTTP functionality through `inject(FETCH_PORT_KEY)` rather than `browser.pyscript.fetch`.

#### Scenario: Ajax uses injected FetchPort
- **WHEN** `webcompy.ajax._fetch` performs an HTTP request
- **THEN** it SHALL call `inject(FETCH_PORT_KEY).fetch(...)` instead of `browser.pyscript.fetch(...)`

### Requirement: Logging uses pyscript.context directly
The `webcompy.logging` module SHALL use `pyscript.context.window.console.log` directly when in PyScript environment, without port abstraction.

#### Scenario: Logging outputs to browser console
- **WHEN** `logging.log()` is called in PyScript environment
- **THEN** it SHALL output via `pyscript.context.window.console.log()`

### Requirement: Effect scheduling uses schedule_macro_task
The signal effect system SHALL schedule deferred callbacks through `inject(DOM_PORT_KEY).schedule_macro_task()`.

#### Scenario: Effects scheduled via port
- **WHEN** `_schedule_effect` runs in PyScript environment
- **THEN** it SHALL use `inject(DOM_PORT_KEY).schedule_macro_task(_flush_pending_effects)`
- **AND** fall back to synchronous execution if injection fails
