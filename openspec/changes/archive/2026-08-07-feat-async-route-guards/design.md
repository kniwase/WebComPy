# Design: Async Route Guards and Redirects

## Decisions

### D1. Guard result contract

```python
GuardResult = bool | str | None
Guard = Callable[[str, str], GuardResult | Awaitable[GuardResult]]
```

- `None` / `True` → allow; `False` → cancel; `str` → redirect.
- `Awaitable` results are awaited and the resolved value interpreted identically. A resolved `None`/`True` allows, etc.
- A guard raising (sync or async) → navigation cancelled, exception routed through `router.on_route_error` (existing contract: `True` suppresses, otherwise propagate). Propagation from an async chain goes to the global error pipeline (`aio._log_error` fallback), consistent with other async error paths.

### D2. The `__set_path__` pipeline (router/_router.py:285-292 rewritten)

```python
def __set_path__(self, path: str, state: dict[str, Any] | None) -> None:
    token = next(self._nav_token_counter)      # itertools.count(1)
    self._latest_token = token
    self._attempt(path, state, token, redirect_depth=0)

def _attempt(self, path, state, token, redirect_depth) -> None:
    if redirect_depth > 10:
        self._route_guard_error(WebComPyRouterException("redirect loop detected"))
        return
    history = self._resolve_history()
    from_path = history.value
    pending: list[Guard] = []
    for guard in self.before_route_change:
        result = guard(from_path, path)
        if isinstance(result, Awaitable):      # collections.abc.Awaitable / inspect.isawaitable
            pending = remaining_guards_after_current
            resolve_async(
                self._continue_async(result, pending, from_path, path, state, token, redirect_depth),
                on_error=self._route_guard_error,
            )
            return
        outcome = self._interpret(result, from_path, path, state, token, redirect_depth)
        if outcome != "allow":
            return                              # cancel/redirect handled inside _interpret
    self._commit(path, state, token)            # sync fast-path: fully synchronous
```

`_continue_async` awaits the pending guard result, interprets it, then loops the remaining guards the same way (sync results processed inline; a further awaitable re-enters `resolve_async` or is awaited directly inside the coroutine — implementation detail: the whole continuation is one coroutine that awaits each awaitable in turn).

Key invariant: **when no guard returns an awaitable, `_attempt` completes entirely synchronously** — URL, signal, and `after_route_change` all happen before `__set_path__` returns, exactly as today.

### D3. Commit and token check

```python
def _commit(self, path, state, token) -> None:
    if token != self._latest_token:
        return                                   # superseded while awaiting
    history = self._resolve_history()
    history.push_url(path, state)                # NEW: browser URL updates only here
    history.navigate(path, state)
    for callback in self.after_route_change:
        callback(path)
```

- Token lives on the Router instance; `_clone_for_request` gets a fresh counter (per-request isolation preserved).
- Superseded chains never push URL, never navigate, never fire `after_route_change`.
- Redirect: `_interpret(str)` calls `self._attempt(redirect_path, None, token, redirect_depth + 1)` — same token (a redirect is one logical navigation) but URL committed with `replace_url` instead of `push_url`. Implementation: `_attempt` gains an `is_redirect: bool` flag threaded to `_commit`, which picks `replace_url` when set.
- Redirect chains re-run the FULL guard list on the target (guards must be redirect-safe; the depth bound protects against loops).

### D4. HistoryPort URL ownership

```python
class HistoryPort:
    def push_url(self, path: str, state: dict[str, Any] | None) -> None: ...      # default: no-op
    def replace_url(self, path: str, state: dict[str, Any] | None) -> None: ...   # default: no-op
```

- Base class no-op keeps server ports and existing fakes valid with zero changes; `webcompy_testing` fake overrides to record calls for assertions.
- `BrowserHistoryPort` implements both via `window.history.pushState/replaceState`, building the href from the path: hash mode → `"#" + path`; history mode → `base_url` prefix when configured. To know `base_url`, `BrowserHistoryPort.__init__` gains an optional `base_url: str = ""` parameter supplied at provisioning time (app config is available there; router already receives base_url today).
- `navigate()` remains pushState-free (signal update only); the pipeline calls `push_url` before `navigate` so signal subscribers see consistent state.
- `state` non-JSON-serializable: keep today's RouterLink behavior — pass `None` to the browser with a warning (logic moves from `_link.py:104-110` into the port/pipeline).

### D5. RouterLink simplification

`_on_click` (`router/_link.py:77-113`) drops the entire `ENVIRONMENT == "pyscript"` pushState block and just calls `self._router.__set_path__(href, params)`. Validation of `query`/`params` shapes stays. `href` attribute generation (`_href`, `_generate_attrs`) is untouched — anchors still carry correct hrefs for open-in-new-tab and SSR.

Edge: RouterLink's `href` includes base_url/mode prefix while `__set_path__` receives that same href today; the pipeline must strip to the app-internal path before guard/matching and re-add prefixes in the port. Router already strips base_url for matching (`_base_url_stripper`); `_attempt` normalizes the incoming path with the same stripper + hash `#` removal, so guards always see clean app paths — same as today (today guards receive the raw href including prefix; this is normalized to app paths, a minor spec-clarified improvement).

### D6. popstate and async guards

popstate is the browser already having moved — guards cannot veto it (the URL is the source of truth). `BrowserHistoryPort._on_popstate` → `_do_navigate` path is UNCHANGED and does not run guards (as today). Guards apply to app-initiated navigations only. Documented explicitly in the spec to set expectations.

### D7. SSR/SSG

- Guards run on the server during SSR/SSG as today (cloned router per request).
- Async guards on the server: `resolve_async` uses `_aio_run_server` (`aio/_aio.py:60`) — tasks scheduled on the running loop. SSR rendering is already async; a guard-triggered navigation completes within the request lifecycle. This matches how other async operations behave server-side.
- `push_url`/`replace_url` are no-ops on server ports: SSR output unaffected.
- Server entry points (`webcompy_cli._server`, `webcompy_testing._asgi`) call `await scheduler.await_pending()` once immediately before page rendering so pending async guard chains settle before serialization. Guards with multi-step async chains that schedule new tasks during the drain may require a loop-drain pattern in the future; current guard patterns are not affected.

### D8. Failure and edge matrix

| Case | Behavior |
|---|---|
| All sync guards pass | fully synchronous navigation (unchanged) |
| Sync cancel | nothing happens; URL untouched (FIXED: previously URL changed) |
| Async guard pending, new `__set_path__` arrives | old chain abandoned at token check; new chain proceeds |
| Async guard resolves `False` | no navigation, no URL, no after hooks |
| Guard returns `/login` | full guard chain re-runs for `/login`; commit uses `replace_url` |
| Redirect ping-pong | depth > 10 → `WebComPyRouterException` via `on_route_error` |
| Guard raises | cancel + `on_route_error`; unsuppressed → error pipeline |
| `after_route_change` raises | propagates as today (unchanged) |
| popstate | no guards (browser owns the URL) — unchanged |

### D9. Spec revision strategy

`router-hooks`'s "shall dispatch synchronously" requirement is MODIFIED (not removed): the sync fast-path guarantee replaces the blanket sync mandate, and the scenario texts are updated. All existing scenarios for cancel/short-circuit/after-hooks remain valid under the fast path.

## Code Structure

```
packages/webcompy/src/webcompy/
├── router/_router.py        # __set_path__/_attempt/_continue_async/_commit/_interpret, token, depth bound
├── router/_link.py          # remove manual pushState block
├── ports/_history.py        # push_url/replace_url (no-op defaults)
├── ports/_browser/_history.py  # browser impls + optional base_url ctor param
└── ports/_server/*, webcompy_testing fakes  # recording overrides for tests
```

## Testing Approach

Server-side unit tests (async guards work in standard Python via `asyncio.run`-driven fake loops or `pytest` async support already used by the async-rendering tests): each D8 matrix row, sync-fast-path synchronicity (assert `after_route_change` fired before `__set_path__` returns), token supersession (start nav A with a pending awaitable, run nav B, resolve A → assert A abandoned), redirect depth, URL recording via fake port. One e2e: protected page + async auth guard → redirect to `/login`, address bar shows `/login`, Back does not loop.
