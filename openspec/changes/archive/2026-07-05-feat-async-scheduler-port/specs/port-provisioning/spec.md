## ADDED Requirements

### Requirement: ASYNC_SCHEDULER_PORT_KEY shall be provisioned in all RenderContext DI scopes

`ASYNC_SCHEDULER_PORT_KEY: InjectKey[AsyncSchedulerPort]` SHALL be defined in `packages/webcompy/src/webcompy/ports/_keys.py` alongside the existing port keys. The `ServerRenderContext._register_ports()` method SHALL provide a `ServerAsyncSchedulerPort` instance via this key. The browser render context SHALL provide a `BrowserAsyncSchedulerPort` instance via this key. The `FakeRenderContext` or equivalent in `webcompy_testing` SHALL provide a `FakeAsyncSchedulerPort` instance.

#### Scenario: ASYNC_SCHEDULER_PORT_KEY in core keys
- **WHEN** a developer writes `from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY`
- **THEN** the key SHALL be importable without installing `webcompy-server`

#### Scenario: Server context provisions ServerAsyncSchedulerPort
- **WHEN** `ServerRenderContext._register_ports()` is called
- **THEN** a `ServerAsyncSchedulerPort` instance SHALL be provided via `ASYNC_SCHEDULER_PORT_KEY` in the DI scope

#### Scenario: Browser context provisions BrowserAsyncSchedulerPort
- **WHEN** the browser render context is initialized
- **THEN** a `BrowserAsyncSchedulerPort` instance SHALL be provided via `ASYNC_SCHEDULER_PORT_KEY` in the DI scope
