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
