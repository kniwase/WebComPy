# Design: Scroll Restoration

## Decisions

### D1. Architecture: a browser-only `ScrollManager` hooked into `HistoryPort`

New module `packages/webcompy/src/webcompy/router/_scroll.py`:

```python
class ScrollManager(Protocol):          # structural type, defined in ports/_history.py to avoid cycles
    def on_push(self, from_path: str, to_path: str) -> None: ...
    def on_pop(self, from_path: str, to_path: str) -> None: ...

class BrowserScrollManager:             # in router/_scroll.py, browser-only instantiation
    def __init__(self, host: HostPort, window: Any) -> None: ...
    def on_push(self, from_path: str, to_path: str) -> None: ...
    def on_pop(self, from_path: str, to_path: str) -> None: ...
```

`HistoryPort` gains:

```python
def set_scroll_manager(self, manager: ScrollManager | None) -> None: ...
```

Call sites (the only two navigation funnels):

- `HistoryPort.navigate()` (`ports/_history.py:56-69`) — the push funnel (RouterLink and programmatic `__set_path__` both end here): after `_do_navigate`, call `manager.on_push(old_value, normalized)`.
- `BrowserHistoryPort._on_popstate()` (`ports/_browser/_history.py:30-44`) — the pop funnel: call `manager.on_pop(old_value, path)` after navigation dispatch (both the `_navigation_callback` override path and the default `_do_navigate` path).

`_on_popstate` DOES funnel through `navigate()` when a Router is attached: the popstate callback registered via `set_navigation_callback` is `Router.__set_path__`, which calls `history.navigate()`. To keep each navigation classified exactly once — push-only from `navigate()`, pop-only from `_on_popstate` — `HistoryPort` carries a `_is_pop_dispatch` flag:

- `HistoryPort.__init__` initializes `self._is_pop_dispatch: bool = False`.
- `BrowserHistoryPort._on_popstate` sets `self._is_pop_dispatch = True` around the dispatch (callback or default `_do_navigate`), restores it in a `finally`, then invokes `manager.on_pop(old_value, path)`.
- `HistoryPort.navigate()` invokes `manager.on_push(old_value, normalized)` after `_do_navigate` only when `self._is_pop_dispatch` is `False`.

`_do_navigate` is never called directly by user code, so each navigation invokes exactly one hook — no double counting.

### D2. Save/restore semantics

`BrowserScrollManager` state: `dict[str, tuple[int, int]]` keyed by the FULL path string the port uses (`pathname + search` in history mode, hash path in hash mode — the same string `HistoryPort.value` carries, so keys are automatically mode-correct).

- `on_push(from, to)`: save `positions[from] = (window.scrollX, window.scrollY)`; schedule scroll-to-top for `to`.
- `on_pop(from, to)`: save `positions[from]`; if `to in positions` schedule restore of that tuple, else schedule scroll-to-top.

Because the outgoing position is saved on EVERY navigation (push and pop alike), Back-then-Forward round trips restore correctly, and positions follow the history entries the user actually saw.

### D3. Post-render scheduling with bounded retry

Scroll actions never run synchronously inside the navigation call (the DOM has not re-rendered yet). Both push and pop schedule via `HostPort.schedule_macro_task` (existing DI port, `ports/_host.py:12`):

```python
def _schedule(self, x: int, y: int, attempts: int = 3) -> None:
    def apply() -> None:
        max_y = document_height - viewport_height
        if y > max_y and attempts > 0:
            self._host.schedule_macro_task(lambda: self._schedule(x, y, attempts - 1))
            return
        window.scrollTo(x, min(y, max_y))
    self._host.schedule_macro_task(apply)
```

- Retry condition: saved `y` exceeds the current scrollable range (content still loading — `Suspense` fallback, lazy route chunk). One retry per macro task, max 3 attempts, then clamp to the maximum scrollable position.
- `scrollTo` coordinates are ints (`int(window.scrollX)`).
- Document height via `document.documentElement.scrollHeight`; viewport via `window.innerHeight` (both available on the raw browser proxy, `_raw.pyi`).

### D4. `scrollRestoration = "manual"` and wiring

- `BrowserScrollManager.__init__` sets `window.history.scrollRestoration = "manual"` exactly once. This is REQUIRED: with the browser default `"auto"`, the browser's own restore races the SPA re-render and wins/loses unpredictably.
- Instantiation happens where the browser `HistoryPort` is provisioned (port-provisioning path), guarded by `ENVIRONMENT == "pyscript"` AND `app config scroll_restoration is True`; the manager is then registered via `history_port.set_scroll_manager(manager)`.
- `WebComPyAppConfig.scroll_restoration: bool = True` (`app/_config.py`, alongside `hydrate`). `False` → no manager created, no `scrollRestoration` mutation: behavior byte-identical to today.

### D5. SSR/SSG: no-op by construction

The manager is only instantiated in the browser and all scroll APIs are reached only through it. Server rendering, SSG, and `webcompy_testing` renderers never touch it; `set_scroll_manager(None)` (default) makes `HistoryPort` behave exactly as before.

### D6. Edge cases

| Case | Behavior |
|---|---|
| Same-path navigation | `HistoryPort.navigate` early-returns on unchanged value+state (line 67-68) → hooks not called → scroll untouched |
| Programmatic `set_path` | goes through `navigate()` → treated as push → top (correct) |
| Direct hash edit / external anchor | arrives via popstate → treated as pop → restore-or-top |
| Page shorter than viewport, saved `y == 0` | `max_y <= 0` and `y == 0` (the natural case — a short page can only have `scrollY == 0`) → `scrollTo(x, 0)`; no retry loop |
| Page currently shorter than viewport with saved `y > 0` | async content pending (Suspense fallback, lazy route chunk) → retried per D3 and restored once the document grows; after 3 attempts clamped to `scrollTo(x, 0)` (spec: "Restore waits for async content") |
| Saved position, content never grows | after 3 retries, clamp to max scrollable |
| Reload on same URL | positions map is in-memory → lost → top (acceptable; browsers still native-restore only if app opted out) |
| Opt-out | config flag; zero side effects |

### D7. Testing without a browser

`BrowserScrollManager` takes `host` and a `window`-like object, so unit tests pass fakes: a fake window with `scrollX/scrollY/innerHeight/scrollTo/history.scrollRestoration` and a fake document height, plus a recording fake HostPort. Tests drive `on_push`/`on_pop` directly. The `HistoryPort` hook invocation is tested with the existing fake/server history port (`webcompy_testing` / `ports/_server`). One e2e scenario: long page → scroll → navigate → assert top → back → assert restored.

## Code Structure

```
packages/webcompy/src/webcompy/
├── ports/_history.py            # + ScrollManager protocol, set_scroll_manager, navigate() hook
├── ports/_browser/_history.py   # + popstate hook
├── router/_scroll.py            # NEW: BrowserScrollManager
└── app/_config.py               # + scroll_restoration: bool = True
```

Wiring (port provisioning / app bootstrap): create + register the manager when building the browser history port, gated on config.

## Dependencies

- No new packages. Uses existing `HostPort`, raw browser proxy (`scrollTo`, `scrollX/Y`, `innerHeight`, `document.documentElement.scrollHeight`, `history.scrollRestoration`).
- Event-handler/proxy invariant: no new event listeners are added (popstate listener already exists); no new `create_proxy` needed.
