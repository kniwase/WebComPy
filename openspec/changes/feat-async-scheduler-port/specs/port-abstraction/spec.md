## ADDED Requirements

### Requirement: AsyncSchedulerPort shall be a port ABC in the port hierarchy

`AsyncSchedulerPort` SHALL be an abstract base class in `packages/webcompy/src/webcompy/ports/_async_scheduler.py`, following the same pattern as `DOMPort`, `FetchPort`, `HostPort`, and other existing ports. It SHALL define `schedule(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]` and `await_pending(self) -> Awaitable[None]` as abstract methods.

#### Scenario: AsyncSchedulerPort ABC definition
- **WHEN** the port hierarchy is inspected
- **THEN** `AsyncSchedulerPort` SHALL be present as an ABC in the `webcompy.ports` package
- **AND** it SHALL define `schedule` and `await_pending` as abstract methods

### Requirement: BrowserAsyncSchedulerPort and ServerAsyncSchedulerPort shall implement AsyncSchedulerPort

`BrowserAsyncSchedulerPort` SHALL be defined in `packages/webcompy/src/webcompy/ports/_browser/_async_scheduler.py` and SHALL only be instantiable when `ENVIRONMENT == "pyscript"`. `ServerAsyncSchedulerPort` SHALL be defined in `packages/webcompy-server/src/webcompy_server/ports/_async_scheduler.py` and SHALL only be used in server environments.

#### Scenario: Browser port instantiation
- **WHEN** `BrowserAsyncSchedulerPort()` is constructed in the pyscript environment
- **THEN** the instance SHALL be created successfully

#### Scenario: Browser port instantiation outside browser
- **WHEN** `BrowserAsyncSchedulerPort()` is constructed in a non-pyscript environment
- **THEN** a `WebComPyException` SHALL be raised
