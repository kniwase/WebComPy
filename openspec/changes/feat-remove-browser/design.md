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
- Introduce `HostPort` ABC with `schedule_macro_task` and `create_js_global_getter`
- Separate `window`-level operations from `DOMPort` into `HostPort`
- Migrate `docs_app` hljs consumers from raw browser import to `HostPort` injection

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

### Decision 6: HostPort separates window-level concerns from DOMPort

`DOMPort` is scoped to document-level operations (element creation, selector queries, title, document event listeners). A new `HostPort` ABC is introduced for window-level operations: JS global object access and macro-task scheduling.

**Rationale**: `document` and `window` are distinct browser API surfaces. Mixing them in `DOMPort` conflates responsibilities. Separating them also allows `HostPort` to carry the `create_js_global_getter` factory — a natural fit since all JS globals live on `window`.

**HostPort API**:
```python
class HostPort(ABC):
    def schedule_macro_task(self, callback: Callable[..., Any]) -> None: ...
    def create_js_global_getter(
        self,
        name: str,
        *,
        wrapper: Callable[[Any | None], T_co] | None = None,
        default: Any | None = None,
    ) -> Callable[[], T_co]: ...
```

- `create_js_global_getter` returns a zero-arg function that lazily resolves `window[name]`
- `wrapper=None` → identity (returns `Any | None`)
- `wrapper=func` → `func(global_obj)` — `T_co` is inferred from wrapper's return type
- `default` → syntactic sugar, returned when the global is missing
- Server-side (`ServerHostPort`) always returns `None` (or `default` if provided)

### Decision 7: schedule_macro_task moves from DOMPort to HostPort

`scheduler_macro_task` (which calls `window.setTimeout(callback, 0)`) is a window-level operation, not a document-level one. It moves to `HostPort`.

- `DOMPort` ABC removes `schedule_macro_task`
- 2 consumer sites (`signal/_effect.py`, `elements/types/_switch.py`) update `inject(DOM_PORT_KEY)` → `inject(HOST_PORT_KEY)`
- `BrowserHostPort` implements via `window.setTimeout`; `ServerHostPort` is no-op

### Decision 8: docs_app hljs consumers migrate from _raw to HostPort

`syntax_highlighting.py` and `demo_display.py` currently import the raw browser object to access `browser.window.hljs`. With `HostPort`, they use `create_js_global_getter("hljs")` instead — a typed, injectable interface that hides the raw browser object.

The getter is created once during component setup and called in `on_after_rendering` / `run_highlight`. This eliminates the last framework-external `_raw` browser references.
