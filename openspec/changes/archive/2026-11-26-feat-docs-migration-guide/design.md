# Design: feat-docs-migration-guide

## Context

The methodology was researched during planning (architecture comparison, strangler via `asgi-embed` host-mount pattern, per-concern mapping). All technical facts are already specified elsewhere: rejected directives (`template-engine`), host embedding (`asgi-embed` + the canonical snippet in ③-8's `asgi-integration` page), middleware auth (`fetch-middleware`/`rpc-middleware`), realtime composables, hydration baking (`server-fetch-asgi`). The guide's job is arrangement and voice for the evaluating reader, not new claims.

## Decisions

1. **Two pages, not a section tree.** Main guide ~600 lines of Markdown in TOC-friendly H2s; compatibility notes as the lookup table page. **Rejected**: 12-page mini-docs — duplication of ③-2/③-8 pages that now exist; the guide should link.
2. **The before/after demo is the anchor.** A user-list search page: Jinja2 column (read-only code blocks) ↔ WebComPy live iframe using a `FetchMiddleware` mock for `/api/users` (works on static export, consistent with ③-9's rule). One narrative walk-through keyed to numbered diff regions. Real FastAPI server code shown as a static block.
3. **Conversion table is the spec-shaped artifact**: rows = Jinja2 construct, status (supported identically / renamed / replaced / rejected), WebComPy form, link. Rendered as a GFM table; the compatibility-notes page carries the fuller matrix including the exact `WebComPyException` messages for rejected directives (helps readers grep errors).
4. **Strangler checklist is phase-based with exit criteria** (Phase 0 host mount smoke → Phase 1 layout + one read-only page → Phase 2 data routes → Phase 3 forms → Phase 4 realtime → Phase N flip `base_url="/"`). Each phase links the Basic/Advanced page that teaches the mechanic used.
5. **Honesty rule reused from ③-1**: where WebComPy is weaker for a Jinja2 team (e.g., no `{% include %}`-style partials with context inheritance semantics, email templates stay server-side — WebComPy targets the SPA surface, not arbitrary string templating), the guide says so and recommends keeping Jinja2 (or plain f-strings) for non-browser HTML.

## Risks / Trade-offs

- [Guide rots as APIs evolve] → every claim links to an owning page; the link-check test (③-6) covers URLs; phase checklist is strategy, slower-moving.
- [Readers assume `render_template` is a Jinja2 drop-in] → lead with the subset/rejection framing plus the error-message matrix.

## Migration Plan

Additive docs + one demo app + Home card. Merge last among docs content changes (links to ③-4/③-8 targets), before ③-11.

## Open Questions

None.
