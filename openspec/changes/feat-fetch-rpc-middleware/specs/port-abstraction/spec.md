# Delta: port-abstraction

## ADDED Requirements

### Requirement: FetchPort shall support middleware wrapping without semantic change

The fetch port system SHALL support wrapping a concrete `FetchPort` implementation in a middleware chain that is itself a valid `FetchPort`. The wrapper SHALL delegate internal lifecycle methods (`populate_from_transfer`, `get_transfer_data`, `clear_cache`, `close`, `is_self_site_url`, and the server-side `noop` marker) to the wrapped implementation. Middleware registration SHALL NOT alter behavior when no middleware is registered.

#### Scenario: Zero-middleware fast path

- **WHEN** no fetch middlewares are registered
- **THEN** `inject(FETCH_PORT_KEY)` resolves to an unwrapped chain equivalent in behavior to the bare port

#### Scenario: Wrapper preserves hydration transfer

- **WHEN** a wrapped server port serves self-site responses during SSR
- **THEN** `get_transfer_data` on the wrapper returns the same entries as the bare port would

### Requirement: Fetch middleware DI keys shall live with port keys

`FETCH_MIDDLEWARE_KEY` and its registry type SHALL be defined alongside the other port DI keys and exported from the ports package, so both browser and server contexts can resolve them without cross-package imports.

#### Scenario: Browser and server parity

- **WHEN** a middleware registry is registered during render-context initialization
- **THEN** both `BrowserRenderContext` and `ServerRenderContext` assemble their chains through the same mechanism
