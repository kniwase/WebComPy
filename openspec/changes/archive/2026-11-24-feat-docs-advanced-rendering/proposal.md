# Proposal: feat-docs-advanced-rendering

## Why

WebComPy's distinguishing capability — the same component tree rendering on server and in browser (SSR/SSG + hydration) plus its async rendering pipeline — has no user-facing documentation at all. Suspense, ClientOnly, Transition, and Teleport (newest: #252/#250/#287) exist only as specs. Advanced pages for styling depth (reactive scoped styles, `css_text_template`, layer order) are equally absent, and the existing Loading Screen page is spec-toned.

## What Changes

- Add six new Advanced Usage pages under `/documents/advanced/`:
  - `ssr-and-ssg` — the two-phase model, `ServerRenderContext`, dev vs prod vs `webcompy generate`, blocked-path fetch, per-request context isolation
  - `hydration-and-transfer` — hydration payload lifecycle (initial-window gating, transfer ids), signal-value transfer and factory-skip, transfer codec, optional compression; flicker-free navigation notes
  - `async-rendering-and-boundaries` — async component setup, `Suspense` (fallback/error/timeout, SSR awaiting), `ClientOnly`, how the scheduler gates the reveal
  - `transition` — `Transition` element, the enter/leave class protocol, duration resolution, reduced motion
  - `teleport` — anchor relocation, SSR default block emission (#287), hydration adoption, target rejection diagnostics
  - `styling-deep-dive` — `css_text`/`css_text_template`, `reactive_scoped_style`, `app.append_style` unlayered contract, full `@layer` cascade model, `:host` advanced patterns
- Revise `loading_screen.md` to the Advanced structure (mode resolution, interaction policies, stages, dormant behavior, custom template toolkit contract).
- Add section grouping inside Advanced Usage (Realtime & RPC / Rendering & Performance / Architecture & Integration) for the sidebar.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: Rendering-block page set + ordering; sidebar subsection grouping (visual grouping within a category without schema churn).

## Impact

- `docs_app/documents/` (6 new `.md`, `loading_screen.md` revision), manifest entries, page wrappers, sidebar grouping support in `docs_app/components/docs_sidebar.py`, `e2e/docs/` new tests
- No package changes; claims traceable to `ssg-via-ssr`, `hydration-data-transfer`, `signal-value-transfer`, `transfer-codec`, `payload-compression`, `async-rendering`, `async-scheduler`, `suspense`, `client-only`, `transition`, `teleport`, `loading-screen`, `css-architecture`, `reactive-scoped-style`, `app-styles` specs

## Known Issues Addressed

None.

## Non-goals

- Server deployment recipes (③-8) and DI/middleware pages (③-6)
- Rewriting realtime/RPC pages (③-4)
- A generated-DOM playground (hydration internals stay prose + code, not interactive)
