## Why

WebComPy currently accesses browser APIs through a single `browser` monolith object imported directly by 18+ files. Before replacing it, the replacement needs to exist. This change adds the port ABC definitions, browser/server implementations, and DI keys as pure additive dead code — no existing file is modified. This establishes the foundation that subsequent phases will migrate consumers onto.

## What Changes

- **NEW** `webcompy/ports/` public package with `__init__.py`
- **NEW** `DOMPort` (ABC): DOM node creation, element querying, title control, macro-task scheduling
- **NEW** `DOMNode` (ABC): explicit-method node interface (`appendChild`, `setAttribute`, `addEventListener`, etc.)
- **NEW** `FFIPort` (ABC): Python↔JavaScript bridge (`create_proxy`, `destroy_proxy`, `is_none`, `to_js`, `assign`)
- **NEW** `FetchPort` (ABC): HTTP requests with a `Response` dataclass
- **NEW** `CookiePort` (ABC): cookie read/write/delete
- **NEW** `HistoryPort` (ABC, extends `SignalBase[str]`): reactive history state + navigation operations. Absorbs the old `Location` class design
- **NEW** Browser implementations for all ports (using `pyscript.context` and `pyscript.ffi`)
- **NEW** Server implementations for all ports (using `httpx` for FetchPort, internal state for others)
- **NEW** DI keys in `webcompy/ports/_keys.py` for all 5 ports

No existing code is modified or removed.

## Capabilities

### New Capabilities

- `port-definitions`: Typed port ABCs (DOMPort, DOMNode, FFIPort, FetchPort, CookiePort, HistoryPort) with dual-environment implementations and DI keys, added as pure additive code with zero consumers.

### Modified Capabilities

(None — this change adds dead code only.)

## Non-goals

- Migrating any existing consumers to use ports (subsequent phases)
- Removing the `browser` object (subsequent phases)
- Changing the Router API (subsequent phases)
- Implementing a Virtual DOM (separate change)

## Impact

- **Affected modules**: `webcompy/ports/` (new package only)
- **No breaking changes** — nothing imports or uses these ports yet
- **New dependency**: `httpx` added to `pyproject.toml` (server-side FetchPort)
- **Testing**: No existing tests affected; no new tests needed until consumers are migrated
