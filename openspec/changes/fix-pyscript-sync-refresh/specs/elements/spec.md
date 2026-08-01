# Delta: elements

## ADDED Requirements

### Requirement: Synchronous refresh dispatch shall not block the event loop in the Pyodide environment

`_run_refresh_sync` SHALL NOT call `loop.run_until_complete` when running in the Pyodide environment (`ENVIRONMENT == "pyscript"`). Instead, the refresh coroutine SHALL be scheduled on the event loop (via the existing `aio_run` mechanism) so it completes fully without raising "Cannot stack switch"; exceptions raised by the refresh SHALL be logged rather than propagated into the DOM event handler. In non-Pyodide environments, `_run_refresh_sync` SHALL keep its current synchronous behavior (`asyncio.run` without a running loop; `nest_asyncio` + `run_until_complete` with one), so a refresh SHALL complete before the call returns.

#### Scenario: Signal-driven refresh from a DOM event handler completes in Pyodide
- **WHEN** a signal-driven refresh (`RepeatElement`, `SwitchElement`, or `MarkdownForElement`) is dispatched from a synchronous DOM event handler in the Pyodide environment
- **THEN** the refresh coroutine SHALL be scheduled on the event loop and run to completion without raising "Cannot stack switch", and no Python traceback SHALL reach the browser console

#### Scenario: Refresh remains synchronous outside Pyodide
- **WHEN** `_run_refresh_sync` is called in a non-Pyodide environment with a running event loop
- **THEN** the refresh SHALL complete synchronously before `_run_refresh_sync` returns (existing behavior preserved)
