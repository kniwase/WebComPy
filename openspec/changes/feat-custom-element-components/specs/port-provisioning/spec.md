## ADDED Requirements

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
