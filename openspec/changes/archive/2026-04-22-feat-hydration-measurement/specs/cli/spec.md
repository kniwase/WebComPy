# CLI — Delta: feat-hydration-measurement

## ADDED Requirements

### Requirement: Generated HTML shall include profiling bootstrap when profile is enabled
When `AppConfig.profile=True`, the generated `<script type="py">` tag SHALL include inline profiling code. When `profile=False` (default), no profiling code SHALL be included and the bootstrap SHALL remain unchanged.

#### Scenario: Generated HTML with profiling enabled
- **WHEN** `AppConfig.profile=True` and a generated `index.html` is examined
- **THEN** the `<script type="py">` tag SHALL start with `import time` and `_pyscript_ready = time.perf_counter()`
- **AND** after the app import, `app._profile_data["pyscript_ready"] = _pyscript_ready` SHALL be present
- **AND** `app.run()` SHALL follow

#### Scenario: Generated HTML with profiling disabled
- **WHEN** `AppConfig.profile=False` (default) and a generated `index.html` is examined
- **THEN** the `<script type="py">` tag SHALL contain only the standard bootstrap (`from <app>.bootstrap import app; app.run()`)
- **AND** no profiling code SHALL appear