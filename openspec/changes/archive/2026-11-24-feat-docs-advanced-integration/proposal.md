# Proposal: feat-docs-advanced-integration

## Why

The remaining Advanced pages split from Basic topics (routing internals, DI depth, middleware chains) plus the integration surfaces (plugins, typed API, headless UI contracts, custom-element interop, cross-tab persistence) have no documentation. These are the pages a team needs before choosing WebComPy for a larger application, and they complete the Basic→Advanced link pairs established in ③-2.

## What Changes

- Add seven new Advanced Usage pages in the `Architecture & Integration` group under `/documents/advanced/`:
  - `routing-deep-dive` — nested `children` and `RouterView` depth/level reuse, `lazy()` + preload behavior, route guards & redirects, scroll restoration contract
  - `dependency-injection-deep-dive` — scope tree semantics, per-render-context isolation, port provisioning, test scopes and helpers
  - `middleware` — `FetchMiddleware`/`RpcMiddleware` chains, ordering and registries, validated `next(response=...)` interception, streaming header-commit resolution, plugin aggregation, hydration delegation
  - `plugins` — `WebComPyPlugin` lifecycle, script plugin loading, custom plugin recipe
  - `typed-api-deep-dive` — `typed-api-client` strictness/coercion, `typed-response` wire modes and pointer maps, `TypedJSONResponse` (FastAPI contrib)
  - `ui-headless-contract` — headless behaviors, `data-state` vocabularies, `class_name` pass-through, three import paths, building a themed pair on a headless core
  - `persistence-patterns` — `sync_tabs` semantics, storage event coalescing, sharing state across tabs, persistence vs hydration
- Revise `custom-elements.md` (relocated by ③-0, stale-text fixed by ③-1) into full interop coverage: Light DOM wrapper boundaries, multiple roots, document-connection hooks, observed attributes → props flow, registration/hydration ordering.
- Land all split-policy back-links promised by Basic pages in ③-2.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: Architecture & Integration block requirement (page set, ordering, back-links).

## Impact

- `docs_app/documents/` (7 new `.md` + `custom_elements.md` revision), manifest + group assignments, page wrappers, `e2e/docs/` tests
- No package changes; content mirrors middleware/routing/DI/plugin/typed specs

## Known Issues Addressed

None.

## Non-goals

- Server-side deployment (③-8); i18n/PWA (③-7)
- Extending the middleware mechanism itself (framework change if gaps appear — out of scope here)
