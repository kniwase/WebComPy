# Design: Error Handling

## Context

WebComPy has no error containment. Tracing the current propagation paths (origin/main @ 6dc7c4c):

| Error source | Current behavior |
|---|---|
| Sync setup / template | `Component._render()` (`components/_component.py:239`) — no catcher; aborts the render pass |
| Async setup | `Component._render()` catches, removes self from `parent._children`, re-raises; contained only inside `Suspense` |
| Signal-driven re-render | callback raises inside `SignalCallback._dispatch()` (`signal/_base.py:59`) → propagates through `consumer_mark_dirty` (`signal/_graph.py:164`) → `producer_notify_consumers` (`signal/_graph.py:117`) → back to the `set_value` caller; subsequent consumers are never notified |
| Event handler (sync) | `_generate_event_handler` (`elements/types/_element.py:24`) — raises into the PyScript proxy; console only |
| Event handler (async) | `resolve_async` (`aio/_aio.py:81`) with default `on_error=_log_error`; logged only |
| `Computed` evaluation | lazy — surfaces at read time, i.e., inside one of the paths above |
| `AsyncResult` | self-contained (`error` signal, `AsyncState.ERROR`); intentionally out of scope |
| SSR | `webcompy_server/_html.py:218` partial handling; uncontained errors 500 the whole page |

The key existing asset is `SuspenseElement._handle_error()` (`elements/types/_suspense.py:184`): it swaps children for a fallback via `_patch_children`, positions nodes with `_position_element_nodes`, and re-indexes siblings. This change generalizes that pattern.

## Decisions

### D1: `ErrorBoundary` is an element, not a component hook alone

**Choice**: `ErrorBoundary = ErrorBoundaryElement`, a `DynamicElement` subclass exported like `Suspense` (`elements/__init__.py` does `Suspense = SuspenseElement`).

```python
ErrorBoundary(
    children=lambda: RiskyWidget(),
    fallback=lambda error, reset: html.div(
        html.p(text=f"問題が発生しました: {error}"),
        html.button(text="再試行", on_click=lambda _: reset()),
    ),
    on_error=None,          # Callable[[Exception], Any] | None — side channel
    catch_events=False,     # opt-in: also catch descendant event-handler errors
)
```

**Why**: Suspense already established the "boundary element with fallback generator" pattern, and fallback UI is inherently a tree concern. **Alternative rejected**: hook-only (Vue-style) — leaves every app to hand-roll fallback UI; element + hook together cover both UI and logic needs.

### D2: Error discovery walks the parent chain

**Choice**: on error, walk `element._parent` upward:

1. Each ancestor `Component` with registered `on_error_captured` hooks is invoked nearest-first. A hook returning `False` marks the error handled; propagation stops (no boundary engages).
2. The first `ErrorBoundaryElement` engages: calls `on_error`, swaps to fallback. Propagation stops; hooks above the boundary are NOT called (React parity).
3. No boundary: report to `WebComPyAppConfig.on_error`, else log.

**Why not ContextVar capture** (`_active_error_boundary` set during render): errors also surface outside any render context — signal callbacks and event handlers fire long after setup. Capturing at registration time would need instrumentation at every subscription site and goes stale if the tree is re-parented. Parent-chain walking works at any time, needs zero registration, and only runs on the exceptional path. **Cost**: O(depth) per error — irrelevant.

**Hook storage**: `context.on_error_captured(fn)` registers into the component instance (new `_error_captured_hooks: list` alongside the existing `_property["on_before_destroy"]` machinery, `components/_component.py:225-234`), following the `_active_component_context` ContextVar pattern of `on_before_destroy` (`components/_hooks.py:40-45`). Hooks are released when the component is destroyed.

### D3: Catch points per error source

| Source | Catch point | Mechanism |
|---|---|---|
| Sync/async setup, initial render | `ErrorBoundaryElement._render()` | try/except around children `_render()`; async-setup re-raise from `Component._render` propagates into this catch (same as Suspense today) |
| Signal-driven re-render | Wrap the internal refresh entry points of `DynamicElement` subclasses (repeat/switch/dynamic) and boundary children re-renders | on exception, route via D2 walk starting at the raising element |
| Event handlers | `_generate_event_handler` (`_element.py:24`) gains a try/except | default: report to global handler; if D2 walk from the element finds a boundary with `catch_events=True`, route to it instead (boundary may swap fallback) |
| Lifecycle hooks | caught at their invocation sites in `Component` | route via D2 walk from the component |
| Errors inside a fallback | the engaging boundary's own render path | re-route via D2 walk **starting above the boundary** — a boundary never catches its own fallback |

Reactive-update instrumentation targets the framework's own refresh callbacks (the closures that call back into `element._render()` / children regeneration), NOT user signal callbacks in general. User callbacks attached via `signal.on_after_updating` are covered by D5's isolation (they don't block others, and their errors go to the global handler) but do NOT engage boundaries — boundaries exist to protect the DOM tree, and a bare callback has no tree context. Rationale: keeps the blast radius of the change small and the semantics explainable.

Implementation refinement (discovered during implementation): refresh/lifecycle/Suspense catch points route via `route_error_deferred`, which performs the hook walk synchronously but SCHEDULES the boundary engagement (via `aio_run`) instead of engaging inline. An inline engagement mid-render destroys the raising subtree while ancestor render loops are still iterating their children, producing orphaned DOM nodes; the scheduled engagement runs after the current render pass settles (server SSR drains scheduled tasks before HTML serialization, so SSR output is unaffected). Only the boundary's own per-child render catch engages inline, where the boundary controls its own loop. Additionally, the propagation walk starts inspection at the error source element itself (not strictly `source._parent`) so hooks registered on a subtree-root component are consulted, and `WebComPyException` (framework validation, e.g. duplicate repeat keys) bypasses routing entirely and propagates as a hard failure.

### D4: `reset()` semantics

- `reset()` destroys the entire children subtree (existing `_remove_element` / component destruction path, including DI-scope disposal) and re-invokes the children generator from scratch. All descendant state is re-initialized (setup re-runs). No state preservation — same as React.
- The responsibility for *when* to reset belongs to the fallback author. If `reset` is never called, the fallback persists indefinitely.
- If the error cause persists, `reset()` simply re-enters the fallback. No infinite loop is possible: `reset()` only fires from external events (clicks, navigation), never from the error path itself.
- The `error` passed to `fallback(error, reset)` is the caught exception instance.
- Boundary state (normal vs fallback) is ephemeral: it is not serialized into hydration payloads and does not participate in reconciliation keys.

### D5: Signal notification isolation (reactive capability)

**Choice**: `producer_notify_consumers` / `consumer_mark_dirty` wrap each consumer's `mark_dirty`+`_dispatch()` so that one raising consumer does not prevent remaining consumers from being notified. The caught exception is reported via the D2/D3 pipeline where a tree context exists, else to the global handler.

- The signal's own value is already committed before notification (`_base.py:138-146`), so isolation cannot corrupt producer state.
- Same-value-set skipping (`old is new or old == new`) and Computed lazy-evaluation contracts are untouched.
- This is a behavior change only for code that was already crashing; it cannot break well-behaved apps.

### D6: Environment policy — SSR tolerant, SSG fail-fast

- **SSR (per-request)**: an engaged boundary renders fallback HTML; the rest of the page renders normally. Uncontained errors keep today's behavior (500).
- **SSG (build time)**: any error reaching a boundary fails the build. Mechanism: the SSG entry point (`webcompy_cli._generate`) provides an injectable strictness flag (new DI key, e.g. `ERROR_POLICY_KEY`, with values `"ssr" | "ssg"`, default `"ssr"`) at render-context creation; `ErrorBoundaryElement` checks `inject(ERROR_POLICY_KEY, default="ssr")` and re-raises when `"ssg"`. DI-key (not env var) keeps the dual-environment rule clean and makes the behavior unit-testable via `webcompy_testing`.

### D7: RouterView implicit boundary

`RouterView._get_or_create_component` (`router/_view.py:91`) wraps each chain level's component in an internal `ErrorBoundaryElement` whose fallback renders nothing (empty) by default. The router's default (`__default__`) component created via `_get_or_create_default_component` is wrapped in the same implicit boundary, so a crashing 404/default view cannot take down the app either.

- **Isolation**: a failing page level cannot take down an ancestor layout level — each level has its own boundary.
- **Reset on navigate**: `RouterView._on_match_changed` (`_view.py:150`) resets the implicit boundary if it is in error state. Because `HistoryPort.navigate` de-duplicates identical path+state and `RouteMatch` has structural equality (so the `_level_match` holder Computed does not re-notify on a same-link click), the reset is driven by `Router.after_route_change`, which fires on every `__set_path__` regardless of de-duplication: `RouterView` registers `_on_navigate_attempt` there and resets an errored boundary whose level identity is preserved. Combined with the level-reuse rule: navigating to an identical match preserves the component, but an errored level retries ("click the same link to retry"); navigating elsewhere destroys the level anyway, so no stale error state survives.
- **Customization**: the implicit boundary's fallback is intentionally minimal (empty). Apps wanting per-route error UI declare their own `ErrorBoundary` inside their page components — explicit boundaries nest inside the implicit one and engage first (D2 nearest-wins).

### D8: Hydration retry (stretch goal)

When SSR rendered a boundary's fallback, the boundary marks its fallback root with a `data-webcompy-error-fallback` attribute. During hydration (`_hydrate_node`), a boundary that adopts marked fallback DOM schedules exactly one automatic `reset()` on the client (via the async scheduler, after initial hydration completes). This rescues server-specific failures (e.g., an SSR-time fetch that the browser can succeed at). If the client attempt fails again, the boundary settles into its fallback as normal. Non-goal if it complicates hydration invariants; the change MUST NOT touch the `AppDocumentRoot._render()` hydration guard.

### D9: Public API surface

- `webcompy.elements`: `ErrorBoundary`
- `webcompy.components`: hook usable via component `context.on_error_captured(...)` (and/or a decorator re-export consistent with existing hooks)
- `webcompy.app`: `WebComPyAppConfig(on_error=...)`
- Fallback signature: `Callable[[Exception, Callable[[], None]], ElementChildren]`

## Code Structure

```
packages/webcompy/src/webcompy/
  elements/types/_error_boundary.py   NEW  ErrorBoundaryElement(DynamicElement)
                                           _render (try/except children), _swap_to_fallback
                                           (reuse _patch_children/_position_element_nodes
                                            pattern from _suspense.py:184-204),
                                           reset(), _find_boundary_walk helpers
  elements/types/_element.py           MOD _generate_event_handler wrap (:24-31)
  elements/types/_dynamic.py           MOD refresh entry-point wrapping
  elements/types/_repeat.py            MOD refresh entry-point wrapping
  elements/types/_switch.py            MOD refresh entry-point wrapping
  elements/__init__.py                 MOD export ErrorBoundary
  components/_hooks.py                 MOD on_error_captured registration
  components/_component.py             MOD hook storage/invocation, lifecycle catch points
  app/_config.py                       MOD WebComPyAppConfig.on_error (:18)
  router/_view.py                      MOD implicit boundary + reset-on-navigate (:91, :150)
  signal/_graph.py                     MOD consumer notification isolation (:117, :164)
  signal/_base.py                      MOD SignalCallback._dispatch error routing (:59)
  di/_keys.py                          MOD ERROR_POLICY_KEY
packages/webcompy-cli/src/webcompy_cli/_generate.py  MOD provide "ssg" policy
```

Direction-of-dependency rule: `error-handling` helpers (the D2 walk) live in `elements/types/_error_boundary.py` and may inspect `Component` via duck-typing or a small protocol to avoid import cycles (`components` already imports `elements`; the walk must not create a hard reverse dependency — use lazy imports like `_suspense.py` does with `Component` at `_hydrate_node`).

## Testing Strategy

- **Unit** (`webcompy_testing.TestRenderer`): matrix of error source {sync setup, async setup, reactive re-render, event handler, lifecycle} × containment {hook veto, boundary engage, catch_events on/off, global handler, none}. `reset()` re-runs setup and restores children; error-in-fallback propagates to the next boundary up; nested boundaries engage nearest-first.
- **Reactive**: raising consumer does not block sibling consumers; producer state remains consistent.
- **SSR/SSG**: SSR renders fallback + rest of page; SSG build raises.
- **Router**: failing level leaves ancestor layout mounted; re-navigation retries.
- **E2E** (`e2e/core/`): a crashing component with a retry button (fallback → reset → healthy), and a page-level crash that leaves the docs-style layout interactive.
