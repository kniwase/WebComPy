## Context

Phase 3 migrated framework consumers to port injection. Phase 4 will migrate `_root_component.py`. Router files (`_link.py`, `_router.py`, `_view.py`, `_change_event_handler.py`) still import `browser` and will be addressed in phase 6. Port implementations themselves (`ports/_browser/*.py`) also depend on the raw browser object.

This phase relocates the browser object definition to an internal location and updates all non-Router import paths. A thin re-export stub preserves compatibility for Router files until phase 6 completes their migration.

## Goals / Non-Goals

**Goals:**
- Create `webcompy/ports/_browser/_raw.py` containing the browser object definition
- Update 6 port implementation files + 1 AJAX fallback to import from `_raw`
- Replace `_browser/_modules.py` with a thin re-export stub (for Router compatibility)
- Remove `browser` from `webcompy/__init__.py` (public export gone)
- Update `pyproject.toml` `stubPath`

**Non-Goals:**
- Migrate Router files (phase 6)
- Delete `_browser/` directory entirely (phase 6, after Router migration)
- Pure-Python browser API replacement (future)

## Decisions

### Decision 1: Browser object moves to `ports/_browser/_raw.py`

The raw browser object definition (currently in `_browser/_modules.py`) is relocated to `webcompy/ports/_browser/_raw.py`. This is an internal implementation detail — not a public export.

### Decision 2: Thin re-export stub preserves Router compatibility

`_browser/_modules.py` is replaced with a one-line re-export:

```python
from webcompy.ports._browser._raw import browser
```

Router files (`router/_link.py`, `router/_router.py`, `router/_view.py`, `router/_change_event_handler.py`) still import from `_browser/_modules` and will continue working unchanged. The `_browser/` directory and its files are fully deleted in phase 6 after all Router migration is complete.

### Decision 3: All port implementation imports updated to `_raw`

Six files under `ports/_browser/` and one AJAX fallback site currently import `from webcompy._browser._modules import browser as _raw_browser`. These are updated to `from webcompy.ports._browser._raw import browser as _raw_browser`:

| File | Old import |
|------|-----------|
| `ports/_browser/_dom.py:5` | `from webcompy._browser._modules import browser as _raw_browser` |
| `ports/_browser/_ffi.py:5` | `from webcompy._browser._modules import browser as _raw_browser` |
| `ports/_browser/_fetch.py:5` | `from webcompy._browser._modules import browser as _raw_browser` |
| `ports/_browser/_history.py:5` | `from webcompy._browser._modules import browser as _raw_browser` |
| `ports/_browser/_cookie.py:5` | `from webcompy._browser._modules import browser as _raw_browser` |
| `ajax/_fetch.py:111` | `from webcompy._browser._modules import browser as _raw_browser` |

### Decision 4: `webcompy/__init__.py` removes `browser`

The public `browser` export is removed. Any external code importing `from webcompy import browser` will get an `AttributeError`. Consumers must use port injection instead.

### Decision 5: `pyproject.toml` stubPath updated

`stubPath = "webcompy/_browser"` → `stubPath = "webcompy/ports"`. The `.pyi` stub at `_browser/_modules.pyi` is removed (unnecessary — ports provide type checking).

## Risks / Trade-offs

- [Risk] A missed consumer still imports `browser` from public API → Mitigation: E2E tests will detect
- [Router breakage] Router files import from `_browser/_modules` which is preserved as a re-export stub → Safe until phase 6
