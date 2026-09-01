# Tasks: feat-docs-advanced-rendering

## 1. Grouping support

- [ ] 1.1 Add optional `group` to `DocsPageEntry`; sidebar sub-header rendering on group change; validation + unit tests (routes/prev-next ignore groups)
- [ ] 1.2 Assign groups to existing Advanced entries (realtime block → `Realtime & RPC`; this change adds `Rendering & Performance` entries in order)

## 2. New pages

- [ ] 2.1 Write `ssr_ssg.md` (pipeline diagram, modes, blocked paths, per-request context isolation) + wrapper + manifest
- [ ] 2.2 Write `hydration_and_transfer.md` (payload lifecycle, transfer ids, signal/async-result/resource transfer, codec tags, compression) + wrapper + manifest
- [ ] 2.3 Write `async_rendering_boundaries.md` (async setup, Suspense incl. SSR awaiting + timeout, ClientOnly, scheduler reveal) + wrapper + manifest
- [ ] 2.4 Write `transition.md` (class protocol table, duration resolution, reduced motion, single-child rule) + wrapper + manifest
- [ ] 2.5 Write `teleport.md` (anchor model, SSR default emission, hydration adoption, rejection diagnostics) + wrapper + manifest
- [ ] 2.6 Write `styling_deep_dive.md` (css_text/css_text_template, reactive scoped styles, app.append_style unlayered, full cascade diagram, :host patterns) + wrapper + manifest

## 3. Revisions

- [ ] 3.1 Rework `loading_screen.md` to the Advanced structure; verify quoted timings against behavior (350/250 ms etc.) and add review-trigger note
- [ ] 3.2 Cross-link pass: Basic styling/routing pages gain Advanced links; async-boundaries links to Error Handling (Basic) and RPC/SSG pages

## 4. Verification

- [ ] 4.1 E2E: new-page titles + TOC + no console errors (prod + static); group headers visible on wide viewport
- [ ] 4.2 `ruff`/`pyright`/unit + `webcompy generate` + docs E2E groups + `check-doc-spec-refs.py` + `openspec validate feat-docs-advanced-rendering`
