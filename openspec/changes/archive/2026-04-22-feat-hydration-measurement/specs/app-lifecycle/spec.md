# Application Lifecycle — Delta: feat-hydration-measurement

## ADDED Requirements

### Requirement: The application shall emit a profile summary after loading screen removal
The application SHALL emit a formatted profiling summary to the browser console (or stdout in server environments) after the loading indicator is removed, when `profile=True`. The summary SHALL show elapsed time between consecutive phases: `pyscript_ready → imports_done`, `imports_done → init_done`, `init_done → run_start`, `run_start → run_done`, `run_done → loading_off`. And a total line with the sum of all measured phases.

#### Scenario: Profiling with profile=True
- **WHEN** a developer creates `WebComPyApp(..., profile=True)` and calls `app.run()` in the browser
- **THEN** the application SHALL record timestamps for each startup phase
- **AND** a formatted profile summary SHALL be printed to the browser console after the loading indicator is removed

### Requirement: WebComPyApp shall provide _record_phase and _emit_profile_summary internal APIs
`WebComPyApp._record_phase(name)` SHALL record `time.perf_counter()` into `_profile_data` only when `_profile` is True. `WebComPyApp._emit_profile_summary()` SHALL format and output the profile summary. In Emscripten, it SHALL use `browser.console.log()`. Otherwise, it SHALL use `print()`.

#### Scenario: Recording a phase with profiling enabled
- **WHEN** `_record_phase("run_start")` is called and `profile=True`
- **THEN** `time.perf_counter()` SHALL be recorded in `_profile_data["run_start"]`

#### Scenario: Recording a phase with profiling disabled
- **WHEN** `_record_phase("run_start")` is called and `profile=False`
- **THEN** no timestamp SHALL be recorded

#### Scenario: Emitting profile summary in browser
- **WHEN** `_emit_profile_summary()` is called in the Emscripten environment
- **THEN** the summary SHALL be output via `browser.console.log()`

### Requirement: WebComPyApp shall expose profile_data property
`WebComPyApp.profile_data` SHALL return `dict[str, float] | None` — the recorded timestamps if profiling was enabled, else `None`.

#### Scenario: Accessing profile data with profiling enabled
- **WHEN** a developer accesses `app.profile_data` on a `WebComPyApp` with `profile=True`
- **THEN** the recorded timestamps dict SHALL be returned

#### Scenario: Accessing profile data with profiling disabled
- **WHEN** a developer accesses `app.profile_data` on a `WebComPyApp` with `profile=False`
- **THEN** `None` SHALL be returned