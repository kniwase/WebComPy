# Port Provisioning

## Purpose

Port provisioning — registering browser or server port implementations into the DI scope — is moved out of `RenderContext.__init__`'s monolithic `if/else` block into subclass-specific `_register_ports()` methods. This ensures core never imports server-side port implementations, and server-side packages can register their own ports without modifying core.

## Requirements

### Requirement: Port registration shall use subclass polymorphism

The `_register_ports()` abstract method on `RenderContext` SHALL be the single extension point for port provisioning. Subclasses SHALL import and provide their environment-specific port implementations. Core SHALL NOT import any `Server*Port` class. `webcompy-server` SHALL NOT import any `Browser*Port` class.

#### Scenario: Core does not import ServerDOMPort
- **WHEN** `webcompy` is imported in any environment
- **THEN** `webcompy.ports._server` SHALL not exist
- **AND** attempting `from webcompy.ports._server import ServerDOMPort` SHALL raise `ModuleNotFoundError`

#### Scenario: Server does not import BrowserDOMPort
- **WHEN** `webcompy_server` is imported
- **THEN** it SHALL only import core modules and port ABCs
- **AND** no `Browser*Port` class SHALL be imported

### Requirement: DI keys shall remain in core

All seven `InjectKey` constants (`DOM_PORT_KEY`, `FFI_PORT_KEY`, `FETCH_PORT_KEY`, `COOKIE_PORT_KEY`, `HISTORY_PORT_KEY`, `HOST_PORT_KEY`, `MEDIA_QUERY_PORT_KEY`) SHALL remain in `packages/webcompy/src/webcompy/ports/_keys.py`. Server and testing packages SHALL import these keys from core.

#### Scenario: Keys importable from core
- **WHEN** a developer writes `from webcompy.ports._keys import DOM_PORT_KEY`
- **THEN** the key SHALL be importable without installing `webcompy-server`

#### Scenario: Server uses core keys
- **WHEN** `ServerRenderContext._register_ports()` is called
- **THEN** it SHALL use `from webcompy.ports._keys import DOM_PORT_KEY, ...` to look up keys

### Requirement: Port ABCs and browser implementations shall remain in core

All seven port ABCs (`DOMPort`, `FetchPort`, `FFIPort`, `HistoryPort`, `HostPort`, `CookiePort`, `MediaQueryPort`) and all seven browser implementations (`BrowserDOMPort`, `BrowserFetchPort`, `BrowserFFIPort`, `BrowserHistoryPort`, `BrowserHostPort`, `BrowserCookiePort`, `BrowserMediaQueryPort`) SHALL remain in `webcompy/ports/` and `webcompy/ports/_browser/` respectively.

#### Scenario: Browser port classes importable from core
- **WHEN** a developer writes `from webcompy.ports._browser._dom import BrowserDOMPort`
- **THEN** the class SHALL be importable
- **AND** it SHALL raise `WebComPyException` if instantiated outside the browser environment

### Requirement: Server port implementations shall live in webcompy-server

All seven server port implementations (`ServerDOMPort`, `ServerFetchPort`, `ServerFFIPort`, `ServerHistoryPort`, `ServerHostPort`, `ServerCookiePort`, `ServerMediaQueryPort`) and the `VirtualDOMNode`/`VirtualDOMEvent` classes SHALL live in `webcompy_server/ports/`. The `_server` suffix SHALL be removed from the path since the package name already disambiguates. `ServerCookiePort` SHALL accept a `cookie_header` string parameter (added in main #178) that is forwarded from `RenderContext.__init__`'s `self._cookie_header`.

#### Scenario: Server port classes importable from webcompy-server
- **WHEN** a developer writes `from webcompy_server.ports import ServerDOMPort`
- **THEN** the class SHALL be importable

#### Scenario: VirtualDOMNode importable from webcompy-server
- **WHEN** a developer writes `from webcompy_server.ports import VirtualDOMNode, VirtualDOMEvent`
- **THEN** both classes SHALL be importable

### Requirement: Plugin-provided ports shall integrate with subclass-based provisioning

Plugins registered via `WebComPyAppConfig.plugins` that provide additional port implementations or override existing ones SHALL continue to work. `PluginManager.init_render_context()` SHALL be called in `RenderContext.__init__` AFTER `_register_ports()`, allowing plugins to override or augment ports provided by the subclass.

#### Scenario: Plugin overrides a port after subclass provision
- **WHEN** a plugin's `init_render_context()` provides a custom `DOMPort`
- **AND** `RenderContext.__init__` calls `_register_ports()` then `init_render_context()`
- **THEN** the plugin's `DOMPort` SHALL override the one provided by `_register_ports()`

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

### Requirement: CUSTOM_ELEMENT_PORT_KEY shall live in core keys

The framework SHALL define `CUSTOM_ELEMENT_PORT_KEY: InjectKey[CustomElementPort]` in `packages/webcompy/src/webcompy/ports/_keys.py` alongside the existing port keys.

#### Scenario: Key importable from core
- **WHEN** a developer writes `from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY`
- **THEN** the key SHALL be importable without installing `webcompy-server`

### Requirement: All render contexts shall provision a CustomElementPort

The browser render context SHALL provide a browser `CustomElementPort` implementation via `CUSTOM_ELEMENT_PORT_KEY`. The server render context SHALL provide a no-op implementation that never accesses browser APIs or creates FFI proxies. The testing render path SHALL provide a fake implementation that records or no-ops registration and binding.

#### Scenario: Browser context provisions the browser port
- **WHEN** a `BrowserRenderContext` is created
- **THEN** `CUSTOM_ELEMENT_PORT_KEY` SHALL resolve to a browser custom-element port
- **AND** the port SHALL be able to define and bind custom elements

#### Scenario: Server context provisions a no-op port
- **WHEN** a `ServerRenderContext` is created
- **THEN** `CUSTOM_ELEMENT_PORT_KEY` SHALL resolve to a no-op port
- **AND** calling its registration or binding methods SHALL not access browser APIs or raise

#### Scenario: Testing path provisions a fake port
- **WHEN** the testing render path provisions ports
- **THEN** `CUSTOM_ELEMENT_PORT_KEY` SHALL resolve to a fake implementation
- **AND** unit tests SHALL run without a browser or PyScript runtime

### Requirement: EVENT_SOURCE_PORT_KEY shall live in core keys

The framework SHALL define `EVENT_SOURCE_PORT_KEY: InjectKey[EventSourcePort]` in `packages/webcompy/src/webcompy/ports/_keys.py` alongside the existing port keys.

#### Scenario: Key importable from core
- **WHEN** a developer writes `from webcompy.ports._keys import EVENT_SOURCE_PORT_KEY`
- **THEN** the key SHALL be importable without installing `webcompy-server`

### Requirement: All render contexts shall provision an EventSourcePort

The browser render context SHALL provide a browser `EventSourcePort` implementation via `EVENT_SOURCE_PORT_KEY`. The server render context SHALL provide a no-op implementation that never accesses browser APIs or creates FFI proxies. The testing render path SHALL provide a fake implementation that records subscriptions and delivers scripted events.

#### Scenario: Browser context provisions the browser port
- **WHEN** a `BrowserRenderContext` is created
- **THEN** `EVENT_SOURCE_PORT_KEY` SHALL resolve to a browser event-source port
- **AND** the port SHALL be able to open native `EventSource` connections

#### Scenario: Server context provisions a no-op port
- **WHEN** a `ServerRenderContext` is created
- **THEN** `EVENT_SOURCE_PORT_KEY` SHALL resolve to a no-op port
- **AND** calling its open method SHALL not access browser APIs and SHALL return a no-op cleanup
- **AND** the port SHALL be marked no-op (`noop`) so the composable can distinguish it from real ports (e.g., testing fakes) resolved outside the browser

#### Scenario: Testing path provisions a fake port
- **WHEN** the testing render path provisions ports
- **THEN** `EVENT_SOURCE_PORT_KEY` SHALL resolve to a fake implementation
- **AND** unit tests SHALL run without a browser or PyScript runtime
