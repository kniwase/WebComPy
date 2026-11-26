# Docs Migration Guide

## Purpose

Defines the `/documents/migration/` documentation category helping server-rendered Python teams move from Jinja2 and FastAPI to WebComPy: an architecture-shift model, ASGI integration topologies anchored by the host-mount strangler path, a live static-safe before/after user-directory comparison, a directive-by-directive mapping and exact error lookup matrix (`compatibility-notes`), and honest scoping links back to the framework's conceptual pages.

## Requirements

### Requirement: A migration guide shall cover Jinja2 + FastAPI teams

docs_app SHALL provide a `Migration` category at `/documents/migration/` containing `from-jinja2-fastapi` and `compatibility-notes`. The main guide SHALL present: the architecture-shift table (request-scoped rendering vs reactive dual-environment), the three integration strategies with the host-mount strangler recommended for migration and linking to the canonical snippet on the ASGI integration page, a directive-by-directive conversion table, per-concern migration mapping (routing split, data fetching with hydration bake, forms, styling, auth, realtime), and a phase checklist with exit criteria. The live before/after user-directory comparison demo (`migration_users`) SHALL style its slotted/child content cleanly without `webcompy-cid` mismatches, synchronize with light and dark theme tokens, and display in a non-clipped iframe. The compatibility-notes page SHALL map every Jinja2 construct to supported/renamed/replaced/rejected with the WebComPy replacement and the exact exception raised for rejected constructs.

#### Scenario: Strategy guidance present

- **WHEN** a FastAPI team opens the main guide
- **THEN** they find a decision section choosing between standalone, mounts-under-WebComPy, and host-mounts-WebComPy with code for each and a warning about `base_url`/mount-prefix pairing

#### Scenario: Rejected directives are mapped, not discovered

- **WHEN** a reader searches for `{% extends %}` in the docs
- **THEN** `compatibility-notes` shows it as rejected with the component-plus-`RouterView` replacement and the error text WebComPy raises

#### Scenario: Before/after demo runs on the static export

- **WHEN** the migration guide's live example loads from the generated static site
- **THEN** the WebComPy column demonstrates search/filtering through its mock data layer with no failed requests
- **AND** its slotted directory items and filter inputs render styled, legible in both light and dark modes, and unclipped

### Requirement: Migration claims shall link, not duplicate

Any technical mechanism the guide relies on (embedding, middleware, hydration transfer, forms) SHALL link to its owning Basic/Advanced/Server page instead of restating the full contract, and the guide SHALL state honestly which server-rendered HTML jobs (e.g., email templates) remain outside WebComPy's scope.

#### Scenario: Canonical snippet referenced

- **WHEN** the host-mount phase is described
- **THEN** the code shown is a minimal excerpt linking to the Server & Tooling ASGI integration page for the canonical version
