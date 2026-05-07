## Context

`WebComPyApp.__init__` currently creates `app.di_scope` and provides `ComponentStore`. Browser/server port implementations were already added by `feat-port-definitions`. The app must provide them to the DI scope during initialization.

## Goals / Non-Goals

**Goals:**
- In PyScript environment: provide `BrowserDOMPort`, `BrowserFFIPort`, `BrowserFetchPort`, `BrowserHistoryPort`
- In server environment: provide `ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerHistoryPort`

**Non-Goals:**
- Remove existing `browser` imports (next phase)
- Change Router API (subsequent phase)

## Decisions

### Decision 1: Ports provided after `_register_deferred_components()`, before `AppDocumentRoot`

`_register_deferred_components()` requires the DI scope, so it runs first. Ports are provided immediately after. They become available before `AppDocumentRoot` is constructed and rendered.

## Risks / Trade-offs

- No risk — ports are not yet required by any component. Addition only.
