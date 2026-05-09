## Context

`Location` (`SignalBase[str]`) provides reactive path state and a popstate listener. `HistoryPort` is an ABC with the same responsibility. The two overlap and must be unified.

## Goals / Non-Goals

**Goals:**
- Delete `Location` and merge all functionality into `HistoryPort`
- `Router` accepts `history: HistoryPort` via constructor
- `RouterView._on_set_parent` updated for HistoryPort compatibility
- `RouterLink` navigates via `inject(HISTORY_PORT_KEY).navigate()`
- `CookiePort` provided in DI scope
- `MockHistoryPort` (extends `HistoryPort`) added for testing
- Rename `_change_event_handler.py` to `_history_events.py` with `type Location = HistoryPort` alias

**Non-Goals:**
- Change RouterMode or base_url API

## Decisions

### Decision 1: HistoryPort extends SignalBase[str]

Inheriting `SignalBase[str]` makes the `value` property reactive. `producer_accessed()` tracks dependencies; `navigate()` increments epoch/version and notifies consumers.

### Decision 2: `navigate()` updates value only, does not call pushState

`RouterLink._on_click` calls `pushState`, and `Router.__set_path__` calls `HistoryPort.navigate()`. `navigate()` only updates the value and triggers reactive notification, avoiding double `pushState`.

### Decision 3: Router receives history as a required constructor parameter

Previously, Router created Location internally. Now it must be injected externally after the DI scope is active.

### Decision 4: Update RouterView._on_set_parent

RouterView injects `_ROUTER_KEY` to get the Router (which holds `HistoryPort` via constructor), and delegates route case evaluation through `router.__cases__` (a `computed_property` that reads from `router._history.value`). No direct `HistoryPort` injection needed in RouterView.

### Decision 5: Rename _change_event_handler.py

Rename `webcompy/router/_change_event_handler.py` to `_history_events.py`. Remove Location code and keep `type Location = HistoryPort` as a type alias (not instantiable; use `BrowserHistoryPort`/`ServerHistoryPort` for construction).

### Decision 6: MockHistoryPort for testing

Add `MockHistoryPort` (extends `HistoryPort`) to `tests/conftest.py`. Enables constructing `Router` in tests without an active DI scope.

### Decision 7: Public API exports

`webcompy/ports/__init__.py` exports all ABCs, `DOMNodeList`, and DI keys. `webcompy/router/__init__.py` removes Location exports.

## Risks / Trade-offs

- [Risk] All existing `Router(mode=...)` calls break → Mitigation: Identify and update all call sites
