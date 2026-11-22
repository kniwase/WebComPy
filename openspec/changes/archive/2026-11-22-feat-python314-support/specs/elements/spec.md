# Delta: elements

## MODIFIED Requirements

### Requirement: DynamicElement `_refresh_sync` pattern shall use a shared helper

A `_run_refresh_sync(refresh: Callable[..., Coroutine[Any, Any, Any]], *args: Any) -> None` helper SHALL be defined in `webcompy/elements/types/_dynamic.py`. The helper SHALL encapsulate the `nest_asyncio2` + `loop.run_until_complete` sync-wrapping logic. `SwitchElement._refresh_sync` and `RepeatElement._refresh_sync` SHALL delegate to `_run_refresh_sync` instead of containing their own copies of the sync-wrapper logic.

#### Scenario: SwitchElement uses shared helper
- **WHEN** `SwitchElement._refresh_sync` is called
- **THEN** it SHALL delegate to `_run_refresh_sync(self._refresh, *args)`
- **AND** the runtime behavior SHALL be identical to the pre-extraction implementation

#### Scenario: RepeatElement uses shared helper
- **WHEN** `RepeatElement._refresh_sync` is called
- **THEN** it SHALL delegate to `_run_refresh_sync(self._refresh, *args)`
- **AND** the runtime behavior SHALL be identical to the pre-extraction implementation

#### Scenario: New DynamicElement subclasses use shared helper
- **WHEN** a new `DynamicElement` subclass (e.g., `MarkdownForElement`) requires `_refresh_sync` semantics
- **THEN** it SHALL use `_run_refresh_sync(self._refresh, *args)` without duplicating the sync-wrapper logic

### Requirement: Synchronous refresh dispatch shall not block the event loop in the Pyodide environment

`_run_refresh_sync` SHALL NOT call `loop.run_until_complete` when running in the Pyodide environment (`ENVIRONMENT == "pyscript"`). Instead, the refresh coroutine SHALL be scheduled on the event loop (via the existing `aio_run` mechanism) so it completes fully without raising "Cannot stack switch"; exceptions raised by the refresh SHALL be logged with a formatted traceback (via `_log_error`, the same logging path used by `_resolve_async_callback`) rather than propagated into the DOM event handler. In non-Pyodide environments, `_run_refresh_sync` SHALL keep its current synchronous behavior (`asyncio.run` without a running loop; `nest_asyncio2` + `run_until_complete` with one), so a refresh SHALL complete before the call returns.

#### Scenario: Signal-driven refresh from a DOM event handler completes in Pyodide
- **WHEN** a signal-driven refresh (`RepeatElement`, `SwitchElement`, or `MarkdownForElement`) is dispatched from a synchronous DOM event handler in the Pyodide environment
- **THEN** the refresh coroutine SHALL be scheduled on the event loop and run to completion without raising "Cannot stack switch"
- **AND** a failed refresh SHALL log a formatted traceback via the logging facility instead of surfacing as an uncaught pageerror

#### Scenario: Refresh remains synchronous outside Pyodide
- **WHEN** `_run_refresh_sync` is called in a non-Pyodide environment with a running event loop
- **THEN** the refresh SHALL complete synchronously before `_run_refresh_sync` returns (existing behavior preserved)
