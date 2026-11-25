# Proposal: feat-docs-migration-guide

## Why

The largest adjacent audience is server-rendered Python teams: FastAPI apps serving Jinja2 templates. WebComPy deliberately does not emulate Jinja2 inheritance (`extends`/`block`/`macro`/`include` are rejected), so migration without guidance means hitting compiler errors with no map. A dedicated guide page set turns that audience into users — this is the docs system's growth lever.

## What Changes

- Add a `Migration` standalone category (`/documents/migration/`) with:
  - `from-jinja2-fastapi` (main guide): architecture-shift table; integration strategy choice (standalone / mounts-under-WebComPy / host-mounts-WebComPy strangler); directive-by-directive conversion table (extends → layout component + `RouterView`, block → slots with fallback, macro → component/helper function, include → component tag, set → Python local, filters → filter registry + helpers); routing split (page vs data routes); context-dict → `HttpClient`/`use_async_result`/RPC with hydration bake explained; forms PRG → `use_form` + `:bind`; global CSS → scoped styles; auth/session via cookies + middleware headers; SSE/WebSocket endpoint reuse; a phase-by-phase strangler checklist; gotchas (blocked paths, base_url pairing, kebab tag requirements, `locals()` context)
  - `compatibility-notes` (smaller): Jinja2 subset/removed-feature matrix with the error each rejected directive raises and its WebComPy replacement
- Add a live before/after example: the same user-list page as Jinja2 (static comparison column with syntax-highlighted template) and as a WebComPy demo (iframe + `FetchMiddleware` mock), with a "why each line changed" walk-through.
- Home + Getting Started get "Migrating from Jinja2 + FastAPI" cards/links.

## Capabilities

### New Capabilities

- `docs-migration-guide`: content requirements for the migration category (strategy selection, conversion tables, live before/after, checklist phases).

### Modified Capabilities

- `docs-site-documents`: Migration standalone category registered (prefix, page set).

## Impact

- `docs_app/documents/migration_*.md` (2), manifest category, wrappers, before/after demo app under `static/_demos/`, Home card, E2E page tests
- No package changes; canonical ASGI host-mount snippet lives in Server & Tooling (`asgi-integration`) and is linked, not duplicated

## Known Issues Addressed

None.

## Non-goals

- Migration from React/Vue/Svelte (Python-team audience only; a later guide can reuse the structure)
- Codemods or automatic template translation tooling
- Django-templates specifics (structure overlaps; content scoped to Jinja2 syntax which Django largely shares — noted as such, not expanded)
