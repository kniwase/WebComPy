## Why

All framework and application consumers have been migrated to port injection. The public `browser` object export (`from webcompy import browser`) is no longer needed. However, port implementations (`ports/_browser/*.py`) and the AJAX FormData fallback still depend on the raw browser object internally.

This phase relocates the browser object definition from its public location (`_browser/_modules.py`) to an internal location (`ports/_browser/_raw.py`), updates all internal import paths, and removes the public export. The old `_browser/` directory itself is deleted after all consumers (including Router in phase 6) are confirmed clear.

## What Changes

- **NEW** `webcompy/ports/_browser/_raw.py` — raw browser object definition (relocated from `_browser/_modules.py`)
- **MODIFIED** `webcompy/ports/_browser/_dom.py`: import path updated to `_raw`
- **MODIFIED** `webcompy/ports/_browser/_ffi.py`: import path updated to `_raw`
- **MODIFIED** `webcompy/ports/_browser/_fetch.py`: import path updated to `_raw`
- **MODIFIED** `webcompy/ports/_browser/_history.py`: import path updated to `_raw`
- **MODIFIED** `webcompy/ports/_browser/_cookie.py`: import path updated to `_raw`
- **MODIFIED** `webcompy/ajax/_fetch.py`: FormData fallback import path updated to `_raw`
- **MODIFIED** `docs_app/components/navigation.py`: migrated to `DOM_PORT_KEY` injection with `add_document_event_listener` / `remove_document_event_listener`
- **MODIFIED** `docs_app/components/syntax_highlighting.py`: import path `webcompy` → `HOST_PORT_KEY` with `create_js_global_getter("hljs")`
- **MODIFIED** `docs_app/components/demo_display.py`: import path `webcompy` → `HOST_PORT_KEY` with `create_js_global_getter("hljs")`
- **NEW** `webcompy/ports/_host.py` — `HostPort` ABC (`schedule_macro_task`, `create_js_global_getter`)
- **NEW** `webcompy/ports/_browser/_host.py` — `BrowserHostPort`
- **NEW** `webcompy/ports/_server/_host.py` — `ServerHostPort` (always returns default/None)
- **MODIFIED** `webcompy/ports/_dom.py`: `schedule_macro_task` moved to `HostPort`
- **MODIFIED** `webcompy/ports/_browser/_dom.py`: `schedule_macro_task` moved to `HostPort`
- **MODIFIED** `webcompy/ports/_server/_dom.py`: `schedule_macro_task` moved to `HostPort`
- **MODIFIED** `webcompy/ports/_keys.py`: added `HOST_PORT_KEY`
- **MODIFIED** `webcompy/app/_app.py`: provide `BrowserHostPort` / `ServerHostPort`
- **MODIFIED** `webcompy/signal/_effect.py`, `webcompy/elements/types/_switch.py`: `inject(DOM_PORT_KEY)` → `inject(HOST_PORT_KEY)`
- **REMOVED** `browser` export from `webcompy/__init__.py`
- **REMOVED** `browser` re-export from `webcompy/_browser/__init__.py`
- **MODIFIED** `pyproject.toml`: change `stubPath` from `_browser` to `ports`

## Capabilities

### Modified Capabilities

- `browser-api`: `browser` public export removed. Browser object lives only as an internal implementation detail under `ports/_browser/_raw.py`.

## Non-goals

- Removing `browser` references within Router files (phase 6)
- Removing the browser object definition entirely (it is still needed by port implementations until a pure-Python alternative exists)
- Deprecation period — unstable release, no backward compatibility needed

## Impact

- **Breaking**: `from webcompy import browser` / `from webcompy._browser import browser` no longer works
- **Affected**: `webcompy/__init__.py`, `pyproject.toml`, `webcompy/_browser/` (deleted), 6 port implementation files (import path update)
