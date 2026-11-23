# Design: feat-docs-advanced-rendering

## Context

The dual-environment pipeline (SSR → hydration → SPA) is WebComPy's core differentiator yet undocumented. Recent behavior contracts worth documenting exactly: hydration payload gated to the initial window with per-instance transfer ids (#271), `adopt & render` unified hydration (#262), `resource_transfer="all-text"` + `ResourcePort.preload()` for flicker-free navigation (#265), Teleport default SSR block emission with comment-node anchors (#287/#267), Transition reduced-motion (#252).

## Goals / Non-Goals

**Goals:** make the two-phase model teachable; boundaries (Suspense/ClientOnly/ErrorBoundary) selectable; styling depth reachable.

**Non-Goals:** implementation walk-throughs (API Reference ③-11 covers signatures); server deployment.

## Decisions

### 1. Six pages, two "mega-topics" deliberately merged

- `ssr-and-ssg` one page: same `create_asgi_app` pipeline powers both; splitting would repeat the pipeline diagram twice.
- `hydration-and-transfer` one page: payload lifecycle + signal/async-result/resource transfer + codec + compression form a single mental model. **Rejected**: four micro-pages (fragmented reading).

### 2. Sidebar subsection grouping without manifest-schema break

Add an optional `group` key inside `DocsPageEntry` (TypedDict already `total=False`): sidebar renders a muted sub-header when the group changes; routes/prev-next ignore grouping. This implements the three Advanced blocks (Realtime & RPC / Rendering & Performance / Architecture & Integration) without nesting sections in the manifest (keeping ③-0's "one level" model). **Alternative rejected**: nested manifest sections — sidebar/route generation rewrite for cosmetic gain.

### 3. Page assignments to groups

```
Rendering & Performance: ssr-and-ssg, hydration-and-transfer,
                         async-rendering-and-boundaries, transition, teleport,
                         loading-screen, styling-deep-dive
Realtime & RPC:          (③-4 pages)
Architecture & Integration: (③-6 pages)
```

Ordering inside the group follows reading dependencies: ssr-and-ssg → hydration → async boundaries → transition/teleport/loading → styling.

### 4. Diagram convention

Rendering pages use ASCII figures in fenced blocks (no images): render-pipeline sequence, payload lifecycle window, Transition class state machine, Teleport anchor flow. Keeps SSG self-contained and diff-friendly.

### 5. Behavior-claim discipline

Every numeric contract (350 ms reveal delay, 250 ms fade, 3-attempt scroll retry, backoff formula) is quoted from the specs at authoring time with a review-trigger note in tasks; specs remain the standard, prose must not contradict them.

## Risks / Trade-offs

- [Hydration internals risk becoming a maintenance magnet] → keep internals at "why it behaves this way" depth; explicit out-of-scope note pointing to API Reference.
- [`group` key touches sidebar rendering — small UI code change in a docs change] → contained to `docs_sidebar.py` + manifest TypedDict; spec scenario pins prev/next ignores groups.

## Migration Plan

Additive pages + one manifest schema extension (optional key) + sidebar render tweak; merge after ③-0 and ③-4 (group headers must appear once the realtime block exists).

## Open Questions

None.
