# Application Lifecycle — Delta: feat-hydration-measurement

## Changes

### Added: Profile summary emission after loading screen removal

The application SHALL emit a formatted profiling summary to the browser console (or stdout in server environments) after the loading indicator is removed, when `profile=True`.

The summary SHALL show elapsed time between consecutive phases:
- `pyscript_ready → imports_done`
- `imports_done → init_done`
- `init_done → run_start`
- `run_start → run_done`
- `run_done → loading_off`

And a total line with the sum of all measured phases.

### Added: _record_phase and _emit_profile_summary internal APIs

`WebComPyApp._record_phase(name)` SHALL record `time.perf_counter()` into `_profile_data` only when `_profile` is True.

`WebComPyApp._emit_profile_summary()` SHALL format and output the profile summary. In Emscripten, it SHALL use `browser.console.log()`. Otherwise, it SHALL use `print()`.

### Added: profile_data property

`WebComPyApp.profile_data` SHALL return `dict[str, float] | None` — the recorded timestamps if profiling was enabled, else `None`.