# Proposal: Hydration Performance Measurement

## Summary

Add opt-in performance profiling to `WebComPyApp` to measure and report the time spent in each phase of application startup and hydration in the browser. This provides the data foundation needed to identify bottlenecks and validate future performance improvements.

## Motivation

WebComPy applications running in the browser via PyScript/Pyodide have significant startup latency, but we currently have no way to quantify how much time is spent in each phase (imports, app initialization, DOM mounting, etc.). Without measurement data, performance optimization efforts are based on guesswork rather than evidence.

## Known Issues Addressed

None (this is a new capability).

## Non-goals

- This proposal does not include any performance optimizations — only measurement.
- This does not cover network-level metrics (download sizes, latency). Those are observable via browser DevTools and Playwright MCP.
- This does not instrument PyScript/Pyodide internals (which are outside WebComPy's control).

## Dependencies

- None. This is a foundational change that subsequent hydration and performance proposals will build upon.

## Design

### Approach

Add a `profile` parameter to `WebComPyApp.__init__()` and `WebComPyApp.run()`. When enabled, timestamps are recorded at key lifecycle points and logged to the browser console via `console.log` (or printed via `print` in server environments).

### Measured Phases

```
Phase                       Timestamp Key          Description
──────────────────────────────────────────────────────────────────────
PyScript ready              pyscript_ready          <script type="py"> starts executing
Imports done                 imports_done            All webcompy and app modules imported
App init done                app_init_done           WebComPyApp.__init__() completed
App run start                app_run_start           app.run() called
App run done                 app_run_done            app.run() completed (first render)
Loading screen removed       loading_removed         #webcompy-loading element removed
```

### Timestamp Capture Points

In `WebComPyApp.__init__()`:
- Record `init_start` at entry
- Record `imports_done` after DI scope setup and component registration
- Record `init_done` after `AppDocumentRoot` construction

In `WebComPyApp.run()` / `AppDocumentRoot._render()`:
- Record `run_start` at entry
- Record `run_done` after first render completes
- Record `loading_removed` when `#webcompy-loading` is removed

In the generated HTML bootstrap (`<script type="py">`):
- Record `pyscript_ready` at the very start of the script body

### API

```python
class WebComPyApp:
    def __init__(self, ..., profile: bool = False):
        self._profile = profile
        self._profile_data: dict[str, float] = {}
        ...

    @property
    def profile_data(self) -> dict[str, float] | None:
        """Returns recorded timestamps if profiling was enabled, else None."""
        ...

    def _record_phase(self, name: str):
        """Record the current time for a phase if profiling is enabled."""
        ...
```

### Output Format

When profiling is enabled and the app finishes rendering, a summary is printed to the browser console:

```
[WebComPy Profile]
  pyscript_ready → imports_done:  0.234s
  imports_done  → init_done:     0.156s
  init_done     → run_start:     0.002s
  run_start     → run_done:      0.089s
  run_done      → loading_off:   0.001s
  ─────────────────────────────────
  Total:                          0.482s
```

### SSG Impact

The `profile` parameter must be stored in `AppConfig` so that `generate_html()` can conditionally include the profiling bootstrap code. When `profile=True`, the generated `<script type="py">` tag wraps the bootstrap code with timestamp recording.

## Specs Affected

- `app` — adds profiling capability to `WebComPyApp`
- `app` — adds `profile` field to `AppConfig`
- `cli` — generated HTML must include profiling code when enabled