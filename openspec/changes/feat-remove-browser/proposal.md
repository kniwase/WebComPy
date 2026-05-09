## Why

All consumers have been migrated to port injection. The `browser` object and `webcompy/_browser/` directory are no longer needed. Remove them to clean up the codebase.

## What Changes

- **REMOVED** `webcompy/_browser/_modules.py` — `browser` object definition
- **REMOVED** `webcompy/_browser/__init__.py`
- **REMOVED** `webcompy/_browser/` directory entirely
- **REMOVED** `browser` export from `webcompy/__init__.py`
- **MODIFIED** `pyproject.toml`: change `stubPath` from `_browser` to `ports`

## Capabilities

### Modified Capabilities

- `browser-api`: `browser` object and `_browser/` module removed. All browser API access is through port injection only.

## Non-goals

- Adding new functionality — pure removal only
- Deprecation period — unstable release, no backward compatibility needed
- Migrating `_browser/_modules.pyi` (unnecessary — ports provide type checking)

## Impact

- **Breaking**: `browser` object removal — all consumers must have been migrated in prior phases
- **Affected**: `webcompy/__init__.py`, `pyproject.toml`, `webcompy/_browser/` (deleted)
