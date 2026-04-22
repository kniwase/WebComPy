# Application Configuration — Delta: feat-hydration-full

## Changes

### Added: AppConfig.hydrate field

`AppConfig` SHALL include a `hydrate: bool = True` field. When `True`, the browser-side app initialization SHALL use full hydration mode, adopting prerendered DOM nodes instead of creating new ones. When `False`, all DOM nodes SHALL be created from scratch.

`WebComPyApp.__init__()` SHALL also accept a `hydrate` parameter directly, reading from `config.hydrate` as fallback when not explicitly provided (same pattern as `profile`).