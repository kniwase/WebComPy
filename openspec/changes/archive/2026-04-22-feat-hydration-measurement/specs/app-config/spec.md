# Application Configuration — Delta: feat-hydration-measurement

## Changes

### Added: AppConfig.profile field

`AppConfig` SHALL include a `profile: bool = False` field. When `True`, the generated HTML SHALL include profiling bootstrap code that captures `pyscript_ready` at the start of the PyScript execution.

The `profile` parameter is also accepted directly by `WebComPyApp.__init__()` and syncs to `AppConfig.profile` when provided.