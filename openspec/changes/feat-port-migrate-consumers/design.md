## Context

With `feat-port-migrate-elements` complete, the remaining non-element consumers (ajax, aio, signal/effect, logging, components) are migrated to port injection in the same manner.

## Goals / Non-Goals

**Goals:**
- ajax: obtain `BrowserFetchPort` via `inject(FETCH_PORT_KEY)`
- aio: replace `browser` → `ENVIRONMENT` guard
- signal/effect: `browser.window.setTimeout` → `inject(DOM_PORT_KEY).schedule_macro_task`
- logging: `browser.console` → `pyscript.context.window.console` (preserving full method set: debug, info, warn, error)
- router/_lazy: `browser.console.warn` → `pyscript.context.window.console.warn`
- components: `browser` truthiness → `ENVIRONMENT == "pyscript"`

**Non-Goals:**
- Remove the `browser` object

## Decisions

### Decision 1: Logging uses `pyscript.context` directly, not port injection

Logging is lightweight and environment-agnostic. It uses `pyscript.context.window.console` directly (full method set: debug, info, warn, error). Not complex enough to warrant a port.

### Decision 2: Ajax.fetch uses port injection

FetchPort has different implementations for browser and server, making DI injection appropriate.

## Risks / Trade-offs

- No risk — pure replacement only
