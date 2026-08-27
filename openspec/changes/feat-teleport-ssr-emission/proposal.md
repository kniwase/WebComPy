# Proposal: Teleport SSR Content Emission

## Why

Teleport is currently absent from SSR/SSG output by design ("anchor-only"): only a comment anchor is emitted at the logical position and the teleported children are mounted client-side after PyScript boot. For statically generated content sites this makes Teleport a second-class citizen of SSG — its content never reaches crawlers or no-JS clients. In WebComPy's own docs site the navbar dropdowns are the only crawl path to all `/sample/*` demo pages, so those pages are unreachable from any initial HTML. Vue 3 renders Teleport content into the target during SSR; WebComPy should do the same now that the comment-node foundation (create_comment on all DOM ports) exists.

## What Changes

- **BREAKING** Server-side rendering and static generation SHALL render Teleport children into the resolved target node by default (Vue 3-style), delimited by machine-readable comment markers (`wc-teleport-block:<n>` / `wc-teleport-block-end:<n>`). The previous anchor-only emission becomes an opt-out via a new `ssr` key in `TeleportProps` (`"ssr": False`).
- **BREAKING** `ServerDOMPort.query_selector` is implemented over the completed server virtual DOM for a documented CSS selector subset (type / `#id` / `.class` / compound selectors, descendant and child combinators, comma groups). It no longer returns `None` unconditionally.
- **BREAKING** Server HTML assembly becomes two-phase: render the document scaffold and app tree first, settle pending async work, drain the per-context Teleport registry by resolving each target against the *completed* virtual DOM and rendering children there, then serialize once.
- **BREAKING** Shared-target node accounting is re-based from "teleported blocks are the last nodes of the target" to "blocks are anchored at their start markers", removing both the tail assumption and the pre-existing limitation that external appends to the target skew block bookkeeping.
- **BREAKING** During hydration a Teleport claims its SSR block, removes the claimed nodes, and regenerates its children through the normal client render path (guaranteeing exactly-once end-state); blocks with unconsumed/missing markers fall back to today's self-mount behavior.
- Targets that resolve inside the application's own rendered subtree (or into `head`) are rejected at emission time with a warning plus anchor-only fallback, enforcing the existing "stable targets outside the reactive tree" requirement at implementation level.
- All previously-hidden server execution rules now apply to Teleport children: async setups participate in settling, Suspense behaves as in normal SSR, and errors reaching boundaries fail SSG builds per the error-handling policy.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `teleport`: The "Server-side rendering shall emit only the anchor" requirement is replaced by default-on emission at the resolved target with marker-delimited blocks, opt-out prop, target-rejection policy, availability matrix, and hydration block-consumption contract. Shared-target accounting moves to marker anchoring.
- `virtual-dom`: Adds requirements for comment serialization safety already introduced earlier plus a new CSS-selector-resolution capability over the virtual DOM used by Teleport emission (selector subset, determinism, no side effects).
- `port-abstraction`: `ServerDOMPort.query_selector` behavior contract changes from "always returns None" to real resolution with fallback semantics; spec text updated accordingly.
- `elements`: Extends the hydration adopt-and-render contract with the Teleport block claim/remove/regenerate path and orphan-sweep behavior on destruction during hydration.

## Impact

- `packages/webcompy/src/webcompy/elements/types/_teleport.py` — props (`ssr`), registry collection, hydration block claiming, shared-target accounting rewrite.
- `packages/webcompy-server/src/webcompy_server/ports/_dom.py`, `ports/_virtual_dom.py` — selector engine, query_selector.
- `packages/webcompy-server/src/webcompy_server/_html.py`, `_context.py` — two-phase assembly, scaffold node capture, registry drain ordering, extra scheduler settle.
- DI: extend the existing `_TELEPORT_REGISTRY_KEY` registry (per-context, no new module globals) to carry ordered pending entries, consumed ids, and shared-target info in both environments.
- `docs_app` — navbar dropdown copy/demo text updates; generated output gains hidden-but-crawlable dropdown menus.
- Tests: unit tests for selector engine/emission/rejection/hydration round-trips; E2E core (prod/static duplication checks) and docs-home (pre-hydration presence of navbar links). Existing tests asserting anchor-only SSR output must be updated.
- Docs/skills: AGENTS.md invariant headings and `.opencode/skills/webcompy-review/SKILL.md` references updated alongside the teleport spec revision; docs site Teleport page rewritten.

## Known Issues Addressed

- Element-system known issue "no general virtual DOM diffing": not fixed here; emission renders once on the server and the client regenerates rather than diffs, deliberately avoiding diff machinery scope creep.
- SSG completeness gap: teleported UI (nav dropdowns, modals, cookie banners) missing from static HTML is resolved for crawled/no-JS clients.

## Non-goals

- Node-preserving adoption of claimed SSR blocks (client regenerates children instead; preserve-optimization deferred).
- Emitting Teleport content into `<head>`.
- Resolving Teleports whose targets were produced by the application's own tree (server rejects them; semantics unchanged client-side).
- Multi-app same-document emission guarantees (asgi-embed secondary apps sharing `body` remain outside the contract; fallback keeps them functional).
- A general-purpose comment/portal element type beyond the Teleport markers.
