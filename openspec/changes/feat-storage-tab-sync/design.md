# Design: Cross-Tab Synchronization for `use_local_storage`

## Spike Gate (Task 1 — abort conditions)

The change is implemented only if the spike confirms ALL of the following in the PyScript runtime. Any "fatal" failure aborts the change; findings are recorded in this design (appendix) and the change is discarded.

| # | Verification | Failure severity |
|---|---|---|
| 1 | `window.addEventListener("storage", create_proxy(handler))` receives events fired by another tab | fatal |
| 2 | `event.key` / `event.newValue` / `event.url` are readable with correct values via the JS proxy | fatal |
| 3 | The writing tab does NOT receive its own event (platform guarantee holds) | non-fatal: if it fires, the apply path must additionally guard by origin comparison |
| 4 | Same-value `setItem` in another tab: does it fire? | non-fatal: informs whether redundant updates need suppression |
| 5 | `removeItem(key)` / `clear()` payload shape (`key`, `newValue === null`) | non-fatal: informs removal semantics |
| 6 | `removeEventListener` + `proxy.destroy()` cleanly detaches (no errors, no further calls) | fatal (framework lifecycle invariant) |

Spike method: temporary page in the e2e app registering a listener and recording received events into the DOM; a Playwright script opens TWO pages in ONE browser context (separate contexts do not share `localStorage`), writes from page B, and asserts page A's recorded events. The spike script becomes the permanent e2e test on success.

## Decisions

### D1. Single shared listener with a key registry (preferred) vs per-instance listeners

**Chosen: one shared listener per app, plus a registry mapping storage key → set of subscriber callbacks.**

- A listener is a `create_proxy`'d Python function — each one crosses the Wasm/JS boundary per event. One listener means one proxy, one `addEventListener`, one cleanup point, regardless of how many `use_local_storage(..., sync_tabs=True)` instances exist.
- Registry: module-private `dict[str, list[Callable[[str | None], None]]]` keyed by storage key, created lazily on first `sync_tabs=True` subscription; the shared listener dispatches `event.key` to the registered callbacks.
- The registry lives behind the app's DI scope provisioning (not a module-global singleton) to respect the "No New Globals" invariant: store it on the app/component-store level or as a DI-provided service. Implementation detail for Task 2: follow the per-app state pattern used for other runtime services; a DI key `STORAGE_SYNC_REGISTRY_KEY` is the expected shape.
- Lifecycle: the shared listener is registered once per app lifetime; `__del__`-style teardown mirrors `BrowserHistoryPort` (`removeEventListener` + `proxy.destroy()`). Individual composable instances register/unregister callbacks in the registry; an instance's callback must not outlive its signal (weakly referenced or explicitly unregistered when the owning component is destroyed — simplest correct approach: keep strong refs in the registry and remove on component `on_before_destroy` when created inside setup; for instances created outside setup, the registry entry lives as long as the signal).

Per-instance listeners were rejected: N proxies × N event deliveries, N cleanup points, no benefit.

### D2. Remote-apply path (loop safety)

Receiving an event MUST NOT go through the public `.value` setter, because the write-back subscription (`on_after_updating → _write`) would re-broadcast to other tabs. Instead:

```python
def _apply_remote(sig: Signal[T], raw: str | None, default: ...) -> None:
    if raw is None:                       # removal
        new = _resolve_default(default)
    else:
        try:
            new = json.loads(raw)
        except (ValueError, TypeError):
            logging.warning(...); new = _resolve_default(default)
    if sig.value == new:                  # equality contract: no-op when converged
        return
    sig._value = new                      # internal update bypassing write-back...
```

Direct `_value` assignment bypasses notifications too, which is wrong (templates must update). The actual mechanism: temporarily detach/flag the write-back — a module-private helper sets a per-instance `_applying_remote` flag, assigns `.value` normally (notifications fire, UI updates), and `_write` returns early while the flag is set. This preserves full reactivity with zero re-broadcast.

Loop termination argument: even if the flag mechanism failed, the writing tab never receives its own event (spike item 3) and equality suppression (`sig.value == new`) stops ping-pong after at most one extra hop. Defense in depth, documented.

### D3. Removal and corrupted-payload semantics

- `newValue === null` (removeItem, or `clear()` where the event has `key === null`): reset to `default` (factory re-invoked if callable). For `clear()` (`key === null`), ALL registered keys reset.
- Corrupted JSON from another tab: warning + reset to `default` (mirrors the read-on-create policy in `_read`).

### D4. API

```python
@overload
def use_local_storage(key: str, default: Callable[[], T], *, sync_tabs: bool = False) -> Signal[T]: ...
@overload
def use_local_storage(key: str, default: T, *, sync_tabs: bool = False) -> Signal[T]: ...
```

- Keyword-only, default `False`. `use_session_storage` unchanged.
- `sync_tabs=True` outside PyScript: no-op (server renders default; no listener).
- Same key with mixed `sync_tabs` values across components: allowed; only instances with `True` react to remote events. Their local writes still propagate to storage normally (so a non-syncing instance's write is still received by syncing instances in other tabs).

### D5. Interaction with the equality contract

`Signal` suppresses notification on equal values. Cross-tab delivery of an identical value is therefore free (no re-render). Spike item 4 determines whether same-value `setItem` even fires; either way behavior is correct — the spike only informs whether the no-op path is exercised.

### D6. SSR/hydration

No transfer involvement (unchanged from storage persistence). During hydration the client setup reads storage directly; a remote write between SSR and hydration is picked up by the read-on-create, so the first client render already reflects it. `sync_tabs` listeners attach at creation in the browser.

## Code Structure

```
packages/webcompy/src/webcompy/storage/
├── __init__.py          # unchanged exports
└── _composable.py       # + sync_tabs kwarg, registry dispatch, _apply_remote, flag-guarded _write
```

DI/registry plumbing per D1 (key in `webcompy/di/_keys.py` if the DI route is taken; otherwise per-app holder following existing per-app state patterns).

## Edge Cases

| Case | Behavior |
|---|---|
| Two tabs write concurrently | last writer wins per tab (platform event order); no merge |
| `clear()` in another tab | all registered keys reset to defaults |
| Event for unregistered key | ignored |
| `sync_tabs=True` on server | no-op; default rendered |
| Instance GC'd while registered | registry entry removed at component destroy (setup-created) or lives with the signal (non-setup) |
| Remote value fails JSON parse | warning + default (D3) |

## Spike Findings (to be filled during Task 1)

All six spike-gate items were verified in the PyScript runtime (e2e app spike page
`e2e/core/my_app/pages/storage_sync_spike.py` + `e2e/core/test_storage_tab_sync.py`,
two pages in one browser context, prod and static serving modes). No fatal failures;
the change proceeds to section 2.

| # | Verification | Result |
|---|---|---|
| 1 | Event reception from another tab | PASS — a `storage` listener registered via `create_proxy` + `addEventListener` receives events fired by another tab, for writes originating both from JS (`localStorage.setItem`) and from Python (`context.window.localStorage.setItem` through the proxy path) |
| 2 | Payload readability | PASS — `event.key` reads as a Python `str`; `event.newValue` reads as `str` for values and is detectable as null via `ffi.is_none`; `event.url` reads as `str` |
| 3 | Writing tab does not receive its own event | PASS — the writing page's event list stayed empty while the other page recorded 1 event per write |
| 4 | Same-value `setItem` firing | Observed: NO extra event — writing the same value again produced 0 additional events. The platform suppresses same-value writes, so the equality-convergence no-op path (D5) is never exercised by real events |
| 5 | `removeItem` / `clear()` payload shape | PASS — `removeItem(key)` fires an event with `key=<the key>`, `newValue=<null>`; `clear()` (with data present) fires an event with `key=<null>`, `newValue=<null>`. Note: `clear()` on an *already empty* storage area fires no event at all (HTML spec: no change → no event) |
| 6 | Clean detach | PASS — after `removeEventListener` + `proxy.destroy()`, the page received no further events and produced no console errors |

Additional implementation-relevant observations:

- The Python-originated write path (`context.window.localStorage.setItem`) is the exact
  path the real `_write` uses, and it fires remote events identically to a JS write.
- Because `clear()` on empty storage fires no event, the D3 "all registered keys reset on
  `clear()`" handler only needs to react to real `clear()` events (data present), which is
  the platform's normal behavior.
