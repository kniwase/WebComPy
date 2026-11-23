# Tasks: feat-docs-advanced-rendering

## 1. Grouping support

- [x] 1.1 Add optional `group` to `DocsPageEntry`; sidebar sub-header rendering on group change; validation + unit tests (routes/prev-next ignore groups)
- [x] 1.2 Assign groups to existing Advanced entries (realtime block → `Realtime & RPC`; this change adds `Rendering & Performance` entries in order)

## 2. New pages

- [x] 2.1 Write `ssr_ssg.md` (pipeline diagram, modes, blocked paths, per-request context isolation) + wrapper + manifest
- [x] 2.2 Write `hydration_and_transfer.md` (payload lifecycle, transfer ids, signal/async-result/resource transfer, codec tags, compression) + wrapper + manifest
- [x] 2.3 Write `async_rendering_boundaries.md` (async setup, Suspense incl. SSR awaiting + timeout, ClientOnly, scheduler reveal) + wrapper + manifest
- [x] 2.4 Write `transition.md` (class protocol table, duration resolution, reduced motion, single-child rule) + wrapper + manifest
- [x] 2.5 Write `teleport.md` (anchor model, SSR default emission, hydration adoption, rejection diagnostics) + wrapper + manifest
- [x] 2.6 Write `styling_deep_dive.md` (css_text/css_text_template, reactive scoped styles, app.append_style unlayered, full cascade diagram, :host patterns) + wrapper + manifest

## 3. Revisions

- [x] 3.1 Rework `loading_screen.md` to the Advanced structure; verify quoted timings against behavior (350/250 ms etc.) and add review-trigger note
  - Behavior-claim review (2026-11-24): verified against `_config.py` and `_html.py` (`reveal_delay_ms=350` max 10000, `fade_out_ms=250` max 10000, `timeout_seconds=30` max 3600, dormant opacity `0.9` / saturation `0.85`, wake-up `0.3s ease`, stage keys and ceilings `35/60/85/93/97%`). Re-verify prose tables if any default or ceiling changes in `webcompy.app._config` or `webcompy_server._html`.
- [x] 3.2 Cross-link pass: Basic styling/routing pages gain Advanced links; async-boundaries links to Error Handling (Basic) and RPC/SSG pages

## 4. Verification

- [x] 4.1 E2E: new-page titles + TOC + no console errors (prod + static); group headers visible on wide viewport
- [x] 4.2 `ruff`/`pyright`/unit + `webcompy generate` + docs E2E groups + `check-doc-spec-refs.py` + `openspec validate feat-docs-advanced-rendering`
