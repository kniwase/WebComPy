# Delta: docs-site-documents

## ADDED Requirements

### Requirement: The i18n and PWA pages shall teach their hard parts

`/documents/advanced/i18n` SHALL include, beyond the standard Advanced structure, a deterministic-locale walkthrough covering the cookie-only persistence path from request to hydration and a failure recipe showing how client-side locale mutation breaks parity. `/documents/advanced/pwa` SHALL explain the build-time generated service worker (and why user JavaScript is not accepted) and present the runtime caching rules as a decision table by resource kind.

#### Scenario: Parity walkthrough present

- **WHEN** the i18n page is read
- **THEN** it contains a section tracing cookie → server locale selection → baked state → browser restore, and a "pitfall" recipe for late client-side locale changes

#### Scenario: Caching decision table

- **WHEN** the PWA page is read
- **THEN** a table maps resource kinds to cache strategies with the configuration snippets that produce each
