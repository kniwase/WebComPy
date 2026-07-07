## MODIFIED Requirements

### Requirement: signal() shall create transferable Signal instances with factory-skip

The `signal()` composable SHALL support three calling contexts:

1. **Inside component setup** (server): factory runs, signal registered in `Context._transferable_signals`
2. **Inside component setup** (browser hydration): factory skipped if payload has value, signal registered in `Context._transferable_signals`
3. **Outside component setup** (module level): factory runs (best-effort), signal registered in `_global_transferable_signals`; if factory fails, `Signal(None)` placeholder is created

For context 3, the signal SHALL be restored later by `app.run()` from the `"__global__"` section of the payload. The timing window between module import and `app.run()` restoration SHALL be documented: consumers SHALL NOT read module-level signal values during this window.

#### Scenario: Module-level signal on server
- **WHEN** `signal(lambda: read_env("API_URL"))` is called at module level during SSR
- **THEN** the factory SHALL run, reading the environment variable
- **AND** the signal SHALL be registered in `_global_transferable_signals`
- **AND** `collect_transfer_data()` SHALL collect the value

#### Scenario: Module-level signal on browser hydration
- **WHEN** the same module is imported on the browser
- **THEN** the factory SHALL attempt to run
- **AND** if the factory fails (DI unavailable), a `Signal(None)` placeholder SHALL be created
- **AND** `app.run()` SHALL later restore the correct value from the payload

#### Scenario: Module-level signal on client-side navigation
- **WHEN** a module is imported during client-side navigation (no SSR payload)
- **THEN** the factory SHALL run (DI may be available at this point)
- **AND** no restoration occurs (no payload)
- **AND** the signal holds the factory-produced value

#### Scenario: Timing window documented
- **WHEN** code reads a module-level signal between module import and `app.run()`
- **THEN** the value MAY be incorrect (placeholder or factory-failure default)
- **AND** this SHALL be documented as a known limitation
- **AND** users needing early-access values SHALL use the `provide/inject` pattern instead
