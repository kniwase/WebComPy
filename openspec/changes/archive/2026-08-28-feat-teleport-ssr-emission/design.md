# Design: feat-teleport-ssr-emission

## Context

Teleport today renders an anchor-only slot during SSR/SSG (`_teleport.py` short-circuits `_render()` outside PyScript); children mount client-side after hydration. Three recent foundations shape this design:

- PR #267 replaced the text anchor with a comment node and added `DOMPort.create_comment()` across browser/server/testing ports plus `VirtualDOMNode` comment support — markers can reuse this directly.
- PR #265 established per-request isolated `RenderContext`s for SSG (same `send_html` path as dev/prod), post-settle head/style collection, and context-scoped transfer resources — a per-context Teleport registry buffer is safe and consistent with "No New Globals".
- The HTML assembly (`webcompy_server/_html.py`) builds one `_HtmlElement` tree and serializes once, then performs string-level injections (`</body>` replace chains for payload/loader, `<head>` content, scoped styles, custom loading template marker). No completed node-tree handle survives rendering today, so selector resolution requires capturing scaffold references.

Server-side target resolution previously did not exist: `ServerDOMPort.query_selector` returns `None`, motivated by "(SSG does not query existing DOM)". This change reverses that posture deliberately.

## Breaking-change policy

WebComPy is in **alpha**. This change is shipping without announcement, without a migration path, and without backward compatibility. Externally visible breakages, enumerated for the record:

1. All Teleports emit their children into SSR/SSG output by default; any pipeline asserting anchor-only output breaks.
2. `TeleportProps` gains an `ssr` key; absence means emission enabled.
3. `ServerDOMPort.query_selector` no longer returns `None` unconditionally; custom ports overriding it trivially may behave differently under composed pages.
4. Target-resolution failure modes shift from silent append-free anchoring to warned fallbacks; resolution into the app subtree / `head` now emits warnings where it previously "worked" (by doing nothing server-side).
5. Shared-target sibling-index guarantees are re-based; code relying on teleported blocks being the trailing nodes of a target may observe different ordering when foreign nodes are appended concurrently.

No compatibility shims, deprecation warnings, or dual-mode defaults beyond the explicit `"ssr": False` opt-out.

## Goals / Non-Goals

**Goals:**

- Static/SSR documents carry teleported content for crawlers and no-JS clients while remaining byte-stable inputs for the existing hydration pipeline.
- Deterministic server↔client matching with safe degradation for stale/mismatched documents.
- Eliminate the "teleported blocks are last nodes" tail assumption in shared-target bookkeeping.
- Keep the client runtime behavior for non-emitted teleports byte-for-byte identical to today.

**Non-Goals:** see proposal.md (node-preserving adoption, `head` targets, app-subtree targets, multi-app same-document contracts, general portal elements).

## Decisions

### D1: Default-on with an `ssr` opt-out prop

`TeleportProps` gains `"ssr": bool` (default `True`). Emission is the framework default because SSG completeness is the product story and Vue-parity behavior is the least surprising mental model; per-callsite opt-out covers closed-world targets (e.g. dynamically created containers that never exist at build time).

*Alternatives*: opt-in flag (rejected: leaves most apps incomplete, defeating the crawlability motivation); auto-detect "resolvable target" (rejected: makes output depend on page composition subtleties and surprises tests).

### D2: Generalized server resolution over a strict CSS subset

Implement `ServerDOMPort.query_selector` against the attached document tree supporting type/class/id selectors, compounds, descendant and child combinators, and comma groups. Everything else raises `ValueError`. Strictness keeps the engine small, testable, and predictable; unsupported-but-resolvable selectors fail loudly instead of partially matching.

*Alternatives*: body-literal string match only (rejected by product direction: middle-of-page targets like `#dialog-root` are the common modal pattern); full CSS engine incl. attribute/pseudo selectors (rejected: large surface, no current caller).

Resolution ordering rules that follow from the capability spec: first depth-first match; read-only walk; comments are never matches. A small pure-function matcher over `VirtualDOMNode` keeps unit testing trivial (no HTTP machinery needed).

### D3: Two-phase assembly with post-settle registry drain

Restructure `generate_html`: keep building the same `_HtmlElement` scaffold (loading, controller script, app root placeholder, body scripts, plugin scripts), but capture references to the rendered `html`/`body` nodes and attach them to the server DOM port before serialization. Pipeline order becomes:

```
render scaffold + app tree      (teleport registers {ordinal, to, ssr?, children}; mounts anchor)
await scheduler.await_pending() (existing settling)
drain teleport registry:        resolve -> reject?/render children under target
await scheduler.await_pending() (children may schedule async work)
collect transfer data           (must observe teleported components too)
serialize html node once
existing string injections      (head content, scoped styles, payload+loader, custom-template marker)
```

Keeping payload/loader injection at the string level preserves known-good behavior and limits blast radius; since accounting moves off the tail assumption (D6), injected scripts landing after emitted blocks are harmless.

*Alternatives*: resolve/inject teleports incrementally during the main pass (rejected: targets may not exist yet mid-render — e.g. a later-in-document static container — and interleaving with app rendering reintroduces index hazards); move every injection into the virtual tree this round (deferred).

Registry drain lives in `_html.py` (it owns scaffold references and knows the app-root node for containment checks). Rejection check = parent-chain walk comparing resolved node against app-root subtree or `head` tag.

### D4: Marker contract and ordinals

Blocks are wrapped with start/end comment markers created via the existing `create_comment` port method:

```
<!--wc-teleport-block:<n>:<urlencoded-selector>--> ...children... <!--wc-teleport-block-end:<n>-->
```

Ordinals come from a monotonic counter on the per-context registry, populated during the main render pass. Document-order traversal of Teleports is identical between the server pass and the hydration pass (both are the element tree's DFS; sequential sibling rendering holds during hydration), so a hydrating Teleport claims "the first unclaimed start marker matching my sequence position and selector". Mismatch degrades to self-mount with a warning (spec'd), keeping stale/pre-emission deploys functional by construction.

*Alternatives*: embed component IDs or content hashes in markers (rejected: coupling to unstable MD5 ids and hash stability across environments for marginal benefit); per-target counters instead of one counter (equivalent correctness given selector filtering; single counter is simpler to reason about when two different selectors resolve to one target).

### D5: Consumption = claim, remove, regenerate at the reclaimed slot

On hydration the Teleport locates its claimed block, records its insertion index, removes markers + enclosed nodes, then runs the standard client render path inserting at the recorded index. This guarantees exactly-once end-state with zero new adoption machinery — reusing proven render paths instead of writing a parallel positional-adoption pipeline whose mismatch edges (version skew, dynamic divergence) would each need bespoke recovery.

The rebuild is invisible in practice: removal/reinsert happens during boot before reveal, and emitted markup reflects initial computed state (closed menus are `display:none`), so nothing flashes.

*Alternatives*: adopt-and-hydrate the prerendered nodes like normal trees (deferred — desirable eventually, but the teleport subtree lives under a *foreign parent*; today's adopt paths assume logical-parent slots. Recorded as a future optimization).

### D6: Marker-anchored shared-target accounting

Replace `base = target.childNodes.length - mounted_direct_counts` with positions derived from each block's anchor slot (claimed index during hydration; tracked block bases thereafter). Recreated blocks insert at recorded slots; growth/shrink of one block shifts following block bases through the existing re-index flow minus the tail assumption. Foreign appended nodes become irrelevant by construction.

*Alternatives*: force emitted blocks after all injected scripts and keep tail logic (rejected: fragile against host pages/embedded apps and self-inflicted by our own payload/loader injection).

### D7: Registry extension, not new keys

Extend the object behind `_TELEPORT_REGISTRY_KEY` (already per-DI-scope): ordered pending entries (server), ordinal counter, consumed-id set (client), per-target block info. No module-level globals. Browser behavior when entries are absent (fresh mounts post-boot) stays exactly today's code paths.

## Risks / Trade-offs

- [Custom loading template swap happens via string replace after serialization] → Task 0 spike verifies ordering with the new single-serialize flow; both operations are independent string surgeries on disjoint substrings, expected clean.
- [Transfer data collected before teleported children render would drop their signals] → drain is ordered strictly before `_collect_transfer_data()`; round-trip unit test asserts signal values transferred for teleported reactive state.
- [Default-on flips SSR output for every app] → accepted alpha breakage, enumerated above; unit/E2E suites updated in the same change.
- [Boot crash/error boundary above navbar leaves unconsumed blocks in DOM] → initial computed styles keep typical rest states hidden; elements delta adds unique-block sweep on destruction; worst case is inert served-markup parity with pre-change behavior.
- [Crawlers treat `display:none` content conservatively] → hidden nav links are a decades-standard dropdown pattern and links are still extracted for discovery; no interactivity is promised to crawlers.
- [Selector engine resolves into third-party static containers embedding the app] → allowed by design ("stable nodes outside the reactive tree"); documented availability matrix covers mixed resolution outcomes.
- [asgi-embed secondary apps sharing `body` could collide ordinals] → out-of-contract per proposal Non-goals; fallback keeps such teleports functional (duplicate-free live copy, leftover inert block possible).
- [`page.content()` read timing in E2E] → read immediately after `wait_until="domcontentloaded"` (pattern proven by the #267 layout regression test).

## Migration Plan

Alpha policy: land on `main`; CI regenerates static artifacts; downstream users pick up behavior on next dependency bump. Rollback = revert the change commits; generated output returns to anchor-only form with no persisted-state concerns.

## Open Questions

(none — the custom-template interference item is task-scoped with a defined fallback: reorder the two string surgeries.)

## Spike Results

(Task 1.1 / 1.2 verification, executed before implementation.)

- **Two-phase serialization is byte-identical.** Replicated `generate_html_impl`'s document construction with a manual flow — build the `_HtmlElement("html", ...)` tree under a `_DummyParent(dummy_div)`, call `doc._render()`, then serialize once via `ServerDOMPort.render_html(dummy.childNodes[0])` — and compared against the one-shot `render_html()` path. Outputs matched byte-for-byte (hydration payload normalized). Serialization timing does not alter emitted bytes; attribute order follows per-node insertion order (`VirtualDOMNode._attributes` dict), which is unaffected.
- **Custom loading template composes cleanly.** The `_LOADING_TEMPLATE_MARKER` `<div id="webcompy-loading" data-wc-template-marker=""></div>` serializes verbatim under the new flow, so the post-serialization `str.replace` contract is unchanged. Baseline probe confirmed default bar structure and injected-custom-template behavior both hold today and are orthogonal to when serialization happens.
- **Pipeline ordering (final):** inside `_generate_html_impl` → construct scaffold + app root → manually `_render()` document → `await scheduler.await_pending()` (first settle) → attach `dummy.firstChild` (document html node) via `ServerDOMPort._attach_document_root()` → drain teleport registry → `await scheduler.await_pending()` (second settle for teleported async children) → single serialize. Outer `generate_html` keeps its own settle + head/scoped-style collection + payload/loader injection unchanged; payload collection therefore naturally observes teleported components' transfer state.
- **`create_comment` parity (task 1.2):** implemented across `DOMPort` ABC (`packages/webcompy/src/webcompy/ports/_dom.py`), browser port, `ServerDOMPort`, and `FakeBrowserDOMPort`; fake HTML parser handles comments (`handle_comment`). Hydration-side comment adoption helpers (`TeleportElement._node_matches_existing` / `_adopt_node`) are directly reusable for anchor adoption; no gaps found.

## Follow-up hardening (post-implementation fixes)

- **Comment-safe marker encoding** — `to` selectors are dash-escaped
  (`-` → `%2D`) after percent-encoding in `block_start_data` /
  `_block_start_marker_data` / sweep matching, so marker comments can never
  carry `--` or a trailing `-`, which would fail `ServerDOMPort` comment
  serialization validation and abort generation.
- **Single ordinal reservation** — `_early_claim_ssr_block` marks the teleport
  resolved, and `_resolve_target` reserves only when unreserved. This keeps
  the server/client ordinal counters aligned so fresh mounts and sweep
  identity checks reference the ordinals issued at claim time.
- **Uniquely-identifiable sweep + prerender guard** — the selector-based
  sweep removes a block only when exactly one unclaimed candidate matches;
  ambiguous cases leave inert served markup per the elements contract. Emission
  and document-root attachment run only under `prerender`.
- **Case-sensitive class matching** — the selector engine lower-cased class
  values on the selector side only, so `.Foo` failed to match
  `class="Foo"`. Class and ID values are now compared case-sensitively on
  both sides (type selectors stay ASCII case-insensitive), matching HTML
  document semantics; pinned in `virtual-dom/spec.md` and unit tests.
- **Marker pair survives empty emission** — `_emit_entry` used to drop the
  start marker when children rendered no nodes, decided before the second
  `await_pending()`. Content arriving via deferred tasks (e.g. an initially
  empty teleported list that gains items during the post-drain settle) then
  landed outside any delimitation and hydration could not claim it. The
  marker pair is now always emitted when target resolution succeeds, so
  deferred content stays inside the block; pinned in `teleport/spec.md`
  and unit tests.
- **Single emission per Teleport** — the server `_render` path enqueued a
  pending entry on every render, and a Teleport whose element tree renders
  more than once server-side (e.g. a router-driven render pass followed by
  the main document render pass) reserved two ordinals: one content block
  plus one phantom empty block. With markers always kept, the phantom block
  became visible and unconsumed after hydration. A per-instance
  `_enqueued` guard makes emission at-most-once per render context; pinned
  in `teleport/spec.md` and unit tests.
