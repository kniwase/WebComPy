# Design: Hydration "Adopt & Render"

## Context

See `proposal.md` — Why / What Changes. The design builds on this verified state:

- The hydration pipeline has two phases today: (1) a synchronous `_hydrate_node()` pass that adopts prerendered DOM nodes (`_adopt_node`, `__webcompy_prerendered_node__`), and (2) an async render pass whose entry points depend on element type. Because `DynamicElement._hydrate_node()` schedules renders only for unmounted children and `DynamicElement._render()` skips mounted children in the hydration pass, adopted content is never rendered (dead reactive wiring) — the failure mode `feat-nested-routes` (#226) patched by dropping adoption in `RouterView._hydrate_node()`.
- Measured consequences: ~90% of SSR DOM nodes are removed and rebuilt on docs pages (218 → 21 surviving on a markdown page); `RepeatElement` destroys all adopted children on its first refresh (unit-verified); the loading overlay is removed without waiting for scheduled route-content renders.
- Existing guarantees we rely on: `elements/spec.md` adopt-and-hydrate (diff-only attribute/text writes), `async-rendering/spec.md` (sync `_hydrate_node`, scheduling through `ASYNC_SCHEDULER_PORT_KEY`, browser-only hydration via the `_hydrate` guard), byte-exact markdown conformance (server and client produce identical content for document pages).
- Server constraints from `fix-ssr-hydration-skip`: hydration must stay browser-only; the server's synchronous await-chain render must remain untouched.

## Goals / Non-Goals

**Goals:**
- One unified hydration contract: adopt AND render, for every element, exactly once.
- Zero DOM node removal for matching SSR content (route subtrees and repeated content included).
- Atomic reveal: routed content is present in the DOM when `#webcompy-loading` is removed.
- Every divergence class (text/attr recoverable, tag/node-count structural) is patched or repaired AND recorded, then reported once.

**Non-Goals:**
- No post-hydration sweep of unadopted SSR nodes (proposal Non-goals).
- No changes to payload serialization, `_hydrate_node()` synchronicity, or the server render path.
- No new module-level globals (records live on the per-app `RenderContext`/DI, per the architecture invariant).

## Decisions

### D1 — Hydration render ownership: "one render per element, owned by the dynamic container that hydrates it"

The hydration pass adopts nodes. The render pass then runs exactly once per element. Ownership:
- Children of a hydrated dynamic container are rendered by the container's own hydration-render schedule. `DynamicElement._hydrate_node()` schedules a hydration-render wrapper for every adopted (mounted) child and the plain `child._render()` for every unmounted child; the container's own `_render` remains the single scheduler of its children. `RouterView._hydrate_node()` keeps scheduling its boundary's render (its post-#226 fix), but the boundary now hydrates its children first (adopts).
- A dynamic container's own machinery initializes inside its `_render` (switch branch state via D2, repeat key map via D3); its mounted children are additionally rendered by the scheduled per-child hydration-render wrappers, and the "render exactly once" property is derived in code from the element's mount state (`_mounted`, `_hydrated`) rather than a global pass.
- Regular containers keep their current inline-render behavior (their children render recursively; no skip exists there).
- Refinement (implementation): mounting a wrapper does NOT need to clear the child's `_hydrated` suppression. Each container owns its children's renders: the wrapper recurses via `ElementWithChildren._render`, and nested dynamic descendants are covered by their own `_hydrate_node`-scheduled wrappers. Clearing `_hydrated` in the wrapper would re-render a mounted container's children a second time, so it is deliberately not done. This supersedes the earlier "render children even when mounted" wording in the design.

Rationale: keeps the existing two-phase structure and the `_hydrated` flag's inline-suppression role; changes only who is allowed to skip. Alternatives considered: (a) a global "hydration-render everything once" repass from the boundary task with all skips disabled — conceptually cleanest (React-style) but requires every refresh path to be idempotent for adopted children and risks rendering non-hydrated unrelated subtrees; (b) leaving RouterView as-is and patching only the parent cleanup — rejected: does not fix repeat/switch/suspense and leaves the #226 trade-off in place.

### D2 — Switch initializes its rendered branch from SSR at hydration time

`SwitchElement._hydrate_node()` (via the base `DynamicElement._hydrate_node()` plus a small override) computes the active branch with the same selection logic as `_select_generator()` and records it as the rendered branch. The first `_refresh` with an unchanged condition then performs no branch replacement, so adopted nodes survive. Existing `_on_set_parent()` callback registration already wires the condition signals; this closes the "first refresh regenerates" gap only.

**Implementation refinement (code review)**: the unchanged-branch path in `_refresh` originally cancelled pending render tasks at the top of the method, which dropped the hydration-render wrappers scheduled for adopted children (deterministically in the fake scheduler, racy in the browser) — adopted branch children never completed a hydration render and nested dynamic elements inside the branch stayed dead, re-introducing the `RuntimeWarning: coroutine … was never awaited` the wrapper scheduling was meant to eliminate. Cancellation is now scoped: it runs only on the inline-render path (all children unmounted, where the inline render replaces the scheduled task) and on the branch-changed path (before `_patch_children` replaces the old branch). The unchanged-branch path with mounted children keeps the scheduled wrappers, so exactly one hydration render completes per child. Regression: `test_switch_adopted_branch_nested_repeat_stays_wired`.

Alternative considered: mark adopted children as "patchable and current" inside `_patch_children` — rejected: the branch index is the switch's own state and initializing it at hydration composes with existing refresh logic unchanged.

### D3 — Repeat's first hydration refresh becomes adopt-aware (partial adoption)

`RepeatElement._hydrate_node()` populates the key map from the current sequence (children already exist via `_on_set_parent()`) and records that at least one child was adopted (`_adoption_preserved`). The first refresh (`_signal_activated` still false) no longer performs the destructive full-rebuild when any child was adopted; instead it repositions the children (`_position_element_nodes` semantics with correct `_node_idx` offsets) and re-populates the key map. Children without an adopted node were created fresh during `_hydrate_node()` (unmounted) and complete their render via their scheduled plain-render task, while adopted (mounted) children complete theirs via the scheduled hydration-render wrappers — so matched SSR nodes survive even when only a subset matches (length differences, per-item tag mismatches). The full-rebuild path remains for repeats where no child was adopted (client-side mounts). Subsequent refreshes use the existing keyed reconciliation.

**Implementation refinement (code review)**: the initial implementation treated adoption as all-or-nothing (`all(child._mounted …)`), so a single unmatched item forced a full rebuild that also destroyed the matched adopted siblings. The flag now uses `any(child._mounted …)`; regression coverage: `test_repeat_len_mismatch_preserves_adopted_nodes`, `test_repeat_partial_adoption_preserves_matched_nodes`.

Alternative considered: leave the full-rebuild and accept the identity loss — rejected: measured SSR node destruction and image/iframe re-loads inside repeated items.

### D4 — Hydration mismatches are recorded at repair points, ingested per RenderContext

Every current silent repair point becomes a reporter: replace `existing.remove()` (tag mismatch, excess-node cleanup) and the text/attr write points with `report_mismatch(class, expected, actual, component_id)` calls that append to a per-request collector reachable via the active `RenderContext` (no module-level accumulator — complies with the "No New Globals" invariant). The collector is a plain Python object owned by `RenderContext`; records are keyed by owning component ID where available.

Rationale: the detection points are already there; adding records does not alter repair behavior. Alternative considered: raising or logging per-mismatch messages — rejected: noisy, and e2e error-level checks must stay green.

### D5 — Aggregated warning and `RenderContext.hydration_report`

After the drain (D6), `AppDocumentRoot._render()` asks the collector for a summary and, if non-empty, emits ONE `logging.warning` with counts by class and by component ID. `RenderContext.hydration_report` exposes the record list (empty collection before hydration or on the server).

**Browser console level (measured)**: the stdlib `logging` record surfaces via the Pyodide lastResort/stderr path and is observed as Playwright console type `error` (not `warning`) in the browser; the E2E regression matches both types accordingly. The Python log level remains `warning`.

### D6 — Scheduler drain gates the loading-indicator removal

`BrowserAsyncSchedulerPort` gains a task registry; `schedule()` records the created task, `await_pending()` gathers and awaits all unfinished recorded tasks (completed ones are dropped; exceptions are already routed to the done-callback logging and do not propagate). `AppDocumentRoot._render()` awaits the drain immediately before the existing loading-removal block. The server scheduler path is unchanged.

**Implementation refinement (found during Step 4)**: `await_pending()` MUST exclude the current task from the gathered set. `app.run()` schedules the main render coroutine (`resolve_async` → `aio_run`) through the SAME `ASYNC_SCHEDULER_PORT_KEY`, so a naive `gather(self._registry)` inside `AppDocumentRoot._render()` gathers its own task → self-deadlock (the browser never reached loading removal; every E2E test timed out waiting for PyScript init). The drain filters out `asyncio.current_task()` and re-checks the registry in a loop until no non-current tasks remain (with the same max-iteration guard as the server port).

Alternative considered: collecting `_pending_render_tasks` from every `DynamicElement` and walking the tree — rejected: duplicates the scheduler's concern and misses tasks scheduled by non-dynamic code.

**Implementation refinement (code review)**: the drain is scoped. `AsyncSchedulerPort.schedule(coro, *, render=False)` and `await_pending(*, only_render=False)` were added; the hydration/render call sites (`DynamicElement._hydrate_node` wrappers, Teleport's post-hydration render, ErrorBoundary `_do_reset`) schedule with `render=True`, while generic `aio_run` tasks (user fetches, refresh callbacks, Suspense `_browser_resolve`) stay unmarked. `AppDocumentRoot._render()` calls `await_pending(only_render=True)` so the loading indicator is removed once the routed content renders complete without waiting for unrelated long-running user tasks — a slow/hung user fetch no longer blocks the reveal (before scoping, every `aio_run` task was registered in the drain set).

**Implementation refinement (second code review)**: the scoped drain SHALL NOT unregister non-render tasks. The initial implementation rebuilt the registry to `[current]` before each gather, which silently dropped every pending non-render task — a later unqualified `await_pending()` then could not await them, contradicting the port contract ("no arguments SHALL await all registered tasks"). The rebuild was unnecessary: loop termination already relies on the `not task.done()` filter after `gather`. The rebuild line is removed; regression `test_await_pending_render_only_keeps_plain_tasks_registered` asserts a plain task remains registered after a render-only drain and is awaited by a subsequent unqualified drain.

### D7 — RouterView converges to the standard hydration path

`RouterView._hydrate_node()` keeps its match-time child creation, then calls `child._hydrate_node()` on the boundary (which eagerly generates its children in `ErrorBoundaryElement._hydrate_node()` and adopts), assigns indexes, and schedules the boundary's render (per the D1 ownership refinement, the `_hydrated` suppression is not cleared; the boundary's children are rendered by their own scheduled hydration-render wrappers). This restores the adoption RouterView lost in #226 while keeping that change's guarantee that the routed component's render still runs.

**Double-render observation (task 1.2)**: browser instrumentation on the docs quickstart page recorded each route-content root (`docs-layout`, `quickstart-page`) being REMOVED twice during hydration, i.e. the route subtree was rebuilt twice. The likely mechanism is the scheduled boundary render task racing the inline render chain: `AppDocumentRoot._render()` awaits the inline chain, whose await points yield to the event loop and let the previously scheduled `boundary._render()` task run mid-chain, creating one full docs-layout, after which a router-derived refresh (or a second boundary pass) replaces it with another. This is not fully pinned down by static analysis, so Step 3 MUST verify with the render-count harness that exactly one render per route component occurs and that the E2E instrumentation shows zero content removals; if the rebuild still happens twice after 3.1, the remaining re-render source SHALL be reported before proceeding (per the stop-and-report rule).

**Step 3/4 findings (recorded)**: (a) The double-render was NOT a route-change: `_on_match_changed` never fired during boot (instrumented). (b) A latent `ErrorBoundaryElement._ssr_fallback_in_dom()` bug was exposed by the RouterView convergence: the FFI `getAttribute` returns a `jsnull` proxy (not Python `None`) for a missing attribute, so `raw is not None` wrongly detected an SSR error-fallback on every route root — the boundary then took the fallback path, left children empty, and the parent cleanup removed the SSR root (one node-count record). Fixed by checking `ffi.is_none(raw)` (the same pattern used elsewhere). (c) Post-hydration, the ONLY remaining rebuilt content is the code-block highlight token spans: browser measurement shows alive 104/218 on quickstart and 137/366 on home, where the dead-node counts (114 and 229) exactly equal the number of `tok-*` spans in the corresponding SSG HTML. The markdown body, headings, TOC, and the route ROOT nodes (`docs-layout`, `quickstart-page`) are identity-preserved. Root cause: `CodeBlock` injects highlight output via `raw_html()`, and `RawHTMLElement._adopt_node()` re-applies `innerHTML` unconditionally on adoption — the wrapper span survives but its token-span children are destroyed and re-parsed. Closure is planned in two parts (see D9): a generic RawHTMLElement adoption fix in this change, and a structured-rendering refactor of `CodeBlock` in change `refactor-codeblock-structured-render`. The E2E regression asserts root identity preservation + absence of hydration-mismatch warnings rather than zero node-removal events, since repositioning emits remove+add mutation events without destroying identity.

### D8 — Per-element roles

| Element | Hydrate | First render after adoption |
|---|---|---|
| Regular elements | adopt + attr/text sync | inline recursion (existing) |
| RouterView | create boundary → `boundary._hydrate_node()` → schedule boundary wrapper | boundary wrapper renders children incl. mounted |
| ErrorBoundary | eager children + adopt (existing) | via boundary wrapper (D7) |
| Switch | adopt; preset rendered branch (D2) | `_render` → `_refresh` early path (children additionally covered by scheduled per-child renders) |
| Repeat | adopt; preset key map (D3) | `_render` → `_refresh` reposition-only path |
| Suspense | resolved: adopt + schedule hydration render for children | scheduled; fallback path unchanged |
| Transition | adopt + activate signal (existing) | scheduled hydration render for children |
| ClientOnly | existing (client children; adopt or create) | existing scheduled path |

### D9 — RawHTMLElement adoption preserves matching content (planned follow-up within this change)

`RawHTMLElement._adopt_node()` SHALL follow the same compare-then-apply pattern already used by `TextElement._adopt_node()`: when the adopted wrapper's existing content (`innerHTML`, or `textContent` when `innerHTML` is unavailable) equals the element's rendered value, the framework SHALL skip the content re-application so the wrapper's prerendered child nodes survive; when the content differs, the value SHALL be re-applied and a mismatch of a new kind `raw_html` SHALL be recorded (`MismatchKind` gains `"raw_html"`, delta spec: five mismatch classes). This closes finding (c) for every `raw_html` consumer at the framework-contract level; the browser measurement acceptance for task 7.4 (`alive ≈ 218/218` on quickstart) is expected to be met after this change (remaining `tok-*` spans survive as inner nodes of the adopted wrapper).

- Comparison caveat: the same HTML string parsed from the same server/client source produces the same DOM and therefore the same serialized `innerHTML`; if serialization ever differs (parser normalization edge cases), the comparison fails toward the current behavior (re-apply + record) — safe fallback.
- `CodeBlock` itself is refactored to structured rendering in change `refactor-codeblock-structured-render` (token spans become framework-managed elements; the raw-HTML wrapper disappears). The two changes are independent: D9 covers the generic `raw_html` contract (public API consumers), the refactor covers `CodeBlock` internals. Token-span identity acceptance for that change is measured after both land.

### D10 — Canonical comparison for raw-HTML adoption (implementation refinement)

Raw string comparison between the rendered value and the adopted wrapper's `innerHTML` produces false mismatches: `highlight()` escapes via `html.escape()` (e.g., `"` → `&quot;`, `>` → `&gt;`), while the browser's HTML serializer writes text content with raw `"` and `>`. The first E2E run of 8.4 caught this: 84 of 114 quickstart token spans were destroyed because the python code block contains quotes. Fix: when the raw comparison fails, `_matches_canonical()` re-parses the rendered value into a throwaway wrapper element via the DOM port and compares the serialization with the adopted node's `innerHTML` (canonical forms). Equal → preserve (no write, no record); still different → patch + record `raw_html`. The fake DOM does not entity-decode, so canonicalization is browser-effective only; unit tests cover the decision logic with exact strings, E2E covers the browser path. Verified: quickstart alive 218/218, home 366/366, all demo pages 100% with zero warnings.

**Follow-up finding (task 9.1)**: the demo pages (helloworld etc.) surfaced a second, independent divergence: `use_state()` auto transfer keys embed the call site's absolute filesystem path (`co_filename`), which differs between SSR (checkout path) and the browser (wheel bundle under `site-packages`), so signal restoration never matched and prerendered highlighted content was wiped client-side. Fixed in D11.

### D11 — Environment-stable auto transfer keys

`_auto_key()` now derives the key from the call site's module identity (`caller_frame.f_globals["__name__"]`, basename fallback) plus line/column, instead of `co_filename`. Module dotted names are identical in the SSR checkout and the wheel bundle, so keys match across environments while remaining distinct per call site (same-line calls still disambiguate by column). Unit tests run both sides in the same environment, which is why the path-dependence went undetected until the `raw_html` diagnostic surfaced it. Verified in the browser: helloworld alive 147/147 (tok 108/108), todo 876/876, fetch 791/791, fizzbuzz 978/978, all with zero warnings.

**Test-fixture consequence (task 9.5)**: the lifecycle E2E app's `render_count` used `use_state`, so with restoration working it displayed the SSR-side hook increments plus the client hydration increment (3) instead of the intended client-only count (1). The counter is now a plain `Signal` (client-local); `count` remains a transferable `use_state` signal. The SSR-side double render of the route component (observed as `LifecyclePage → AppRoot → LifecyclePage`) is pre-existing and out of scope.

### D12 — Hydration fallback creates and reuses a single node

The hydration fallback path (`_hydrate_node()` with no matching prerendered node, or a tag mismatch) SHALL create exactly one node per element and record it as the element's node cache, so a later `_get_node()`/render reuses it. The initial implementation (inherited from the pre-change baseline) created the node in `_hydrate_node()` but discarded it, and the subsequent `_get_node()` → `_init_node()` created a second node — an orphan with duplicated `_init_new_node` side effects (attributes, event listeners, ref binding) per unmatched element. The D3 partial-adoption and switch-branch paths make the fallback the common route for unmatched positions, activating the duplication. Fix: `ElementAbstract._hydrate_node()` stores the created node as `_node_cache`. Empty-run text normalization on a fresh (empty) node is a no-op (early return), and repeat `_reconcile_children` additionally avoids a redundant inline render for a node that already has a scheduled hydration render. Regression: `test_hydration_fallback_creates_single_node` (node-creation counting), `test_fallback_element_reuses_created_node` (`_create_node` invocation count and cache identity).

Alternative considered: leave the fallback creation to `_init_node()` only and drop the `_create_node` call from `_hydrate_node()` — rejected: `_hydrate_node()`'s return contract and the existing removal of the stale node are unchanged by the D12 approach, keeping the change minimal.

## Risks / Trade-offs

- **[Exactly-once render violations in deep nesting]** (switch inside repeat inside suspense, etc.) → Mitigation: per-element unit tests assert render call counts and zero REM mutations, including the adopted-Switch-branch nested-dynamic regression; E2E asserts zero node-removal events on docs pages.
- **[Render-task tagging completeness]** — a render call site that forgets `render=True` would let the drain return before its content renders (reveal race) → Mitigation: all `scheduler.schedule(...)` call sites are audited (the six framework call sites; generic `aio_run` tasks are deliberately unmarked); scheduler unit tests cover the filter, and the docs E2E assert content presence at reveal.
- **[`_hydrated` semantics grow subtler]** — the flag now suppresses the inline chain AND marks scheduled wrappers → Mitigation: keep the flag per-element as today; document the two uses; rely on the existing `test_dynamic_child_node_index.py` and new regression coverage.
- **[Legitimate mismatch content is still repaired (removed)]** — e.g., the e2e nested-routes app's module-level signals render fresh values client-side → Mitigation: this is by-design repair (recorded, aggregated warning at `warning` level); e2e asserts only error-level console cleanliness, so suites stay green.
- **[FakeAsyncSchedulerPort in tests]** returns non-running placeholder tasks; drain semantics must be replicated there or tests will hang → Mitigation: update `webcompy_testing` scheduler to track and await scheduled coroutines (existing `_EagerScheduler` test pattern is the shape).
- **[Navigation flows]** (`_on_match_changed`, `_ancestor_will_remount`) depend on mount state of RouterView children → Mitigation: e2e nested-routes suite (sibling/param/query navigation) runs as regression gate.
- **[Hydration mismatch window leak on render failure]** — an exception in the app render chain previously left `_hydration_in_progress` set, so `record_mismatch` kept appending records for the page lifetime → Mitigation: the flag is reset in the `AppDocumentRoot._render()` `finally` block (covered by `TestHydrationWindowClose`).
- **[Perf on large documents]** — the adopted tree now renders once in-place (today it renders after a full rebuild) → expected neutral; verified with profile mode on the quickstart/installation pages.

## Migration Plan

- No user-facing migration: internal framework change; public addition is `RenderContext.hydration_report`.
- Rollback: revert the change; no persisted state or data-format impact (payload untouched).
- Deploy/verify order: unit tests (fake browser) → `webcompy generate` SSG smoke → dev-server SSR smoke → E2E (core + docs) → MutationObserver measurement script re-run (alive ≈ 218/218, zero REM events for content).