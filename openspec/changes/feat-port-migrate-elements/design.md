## Context

Six files in `webcompy/elements/` import the `browser` object and use it for DOM operations and event proxies. `feat-port-definitions` has already defined and implemented DOMPort and FFIPort. This phase switches those consumers to DI injection.

## Goals / Non-Goals

**Goals:**
- `browser.pyscript.ffi.create_proxy(event_handler)` → `inject(FFI_PORT_KEY).create_proxy(event_handler)` (with `ENVIRONMENT` guard)
- `browser.document.createElement(tag)` → `inject(DOM_PORT_KEY).create_element(tag)`
- `browser.document.createTextNode(text)` → `inject(DOM_PORT_KEY).create_text_node(text)`
- `browser.window.setTimeout(cb, 0)` → `inject(DOM_PORT_KEY).schedule_macro_task(cb)`
- `if browser:` → `if ENVIRONMENT == "pyscript":` (equivalent environment guard)
- `browser is not None` → `ENVIRONMENT == "pyscript"` (equivalent environment guard)
- `not browser:` → `ENVIRONMENT != "pyscript":` (equivalent environment guard)

**Non-Goals:**
- Remove the `browser` object (subsequent phase)
- Migrate other packages (next phase)
- Change Router API (subsequent phase)

## Decisions

### Decision 1: Environment guards are exactly equivalent to browser guards

`browser` is truthy in PyScript and falsy otherwise. `ENVIRONMENT == "pyscript"` is exactly equivalent, so simple replacement suffices.

### Decision 2: Event handler proxies are created only inside `_generate_event_handler`

`_generate_event_handler` already has an `if browser:` guard. Replace it with `if ENVIRONMENT == "pyscript": inject(FFI_PORT_KEY).create_proxy(event_handler)`.

### Decision 3: Migration patterns for `if browser:` branching logic

**Pattern A — Guarding browser-only operations:**
```python
# Before
if browser:
    browser.document.createElement("div")
else:
    raise WebComPyException(...)
# After
if ENVIRONMENT == "pyscript":
    inject(DOM_PORT_KEY).create_element("div")
else:
    raise WebComPyException(...)
```

**Pattern B — Branching between browser and server rendering paths:**
```python
# Before
if browser:
    browser.window.setTimeout(callback, 0)
# After
if ENVIRONMENT == "pyscript":
    inject(DOM_PORT_KEY).schedule_macro_task(callback)
```

**Pattern C — Environment-dependent behavior not covered by ports:**
```python
# Before (in _repeat.py, _dynamic.py)
if browser:
    # browser-specific rendering logic
# After
from webcompy.utils import ENVIRONMENT
if ENVIRONMENT == "pyscript":
    # browser-specific rendering logic
```

## Risks / Trade-offs

- [Risk] Server-side `else: raise WebComPyException` path disappears → Mitigation: Server-side `ENVIRONMENT != "pyscript"` code paths exist separately and DOM operations are not executed there
