## ADDED Requirements

### Requirement: The profiling summary shall include startup cost clusters beyond the core phases

When profiling is enabled (`profile=True`), `WebComPyApp._record_phase` SHALL also record two additional startup phases that account for the measured cost clusters: a custom-element bulk-registration phase recorded around the hydration-time bulk `customElements.define` pass, and a lazy-preload phase recorded around the router's lazy-route preload batch. Phases SHALL be recorded at most once each (the first occurrence wins), and the formatted summary SHALL include the elapsed time between these phases and their adjacent phases so the output shows both the core lifecycle phases and the new cost clusters.

#### Scenario: Profiling summary includes the custom-element bulk-registration phase

- **WHEN** an app runs in the browser with `WebComPyAppConfig(profile=True)` and named components are registered before hydration
- **THEN** `app._profile_data` SHALL contain a phase recorded around the bulk custom-element registration pass
- **AND** the formatted profile summary SHALL show the elapsed time associated with that phase

#### Scenario: Profiling summary includes the lazy-preload phase

- **WHEN** an app with lazy routes runs with `profile=True` and `preload=True` (default)
- **THEN** `app._profile_data` SHALL contain a phase recorded around the lazy-route preload batch
- **AND** the formatted profile summary SHALL show the elapsed time associated with that phase

#### Scenario: Phases are recorded at most once

- **WHEN** a profiled phase's recording site is reached more than once during a run
- **THEN** only the first occurrence SHALL be recorded in `app._profile_data`

#### Scenario: Profiling remains disabled by default

- **WHEN** `profile=False` (the default) and an app runs
- **THEN** no new phase timestamps SHALL be recorded, preserving the zero-overhead default behavior