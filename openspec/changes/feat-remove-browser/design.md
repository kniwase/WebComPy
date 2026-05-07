## Context

The `browser` object was defined in `webcompy/_browser/_modules.py` and imported by 18 consumer files. All consumers have been migrated to port injection in prior phases, so removal is safe.

## Goals / Non-Goals

**Goals:**
- Delete `webcompy/_browser/` directory and all its contents
- Remove `browser` export from `webcompy/__init__.py`
- Update `pyproject.toml` `stubPath`

**Non-Goals:**
- Migrate `webcompy/_browser/_modules.pyi` (unnecessary — ports provide type checking)

## Decisions

### Decision 1: Remove `_browser/` entirely

No trace of the old `browser` object remains. WebComPy is an unstable release; no deprecation period is needed.

## Risks / Trade-offs

- [Risk] A missed consumer still imports `browser` → Mitigation: E2E tests will detect
