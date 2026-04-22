# Application Configuration — Delta: feat-wheel-split

## Changes

### Added: AppConfig.version field

`AppConfig` SHALL include a `version: str | None = None` field. When provided, the wheel METADATA SHALL use this version string. When `None`, a timestamp-based fallback SHALL be used. The wheel URL SHALL NOT include the version — it remains stable for browser caching.