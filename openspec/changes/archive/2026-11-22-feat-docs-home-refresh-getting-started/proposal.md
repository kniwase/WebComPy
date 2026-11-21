# Proposal: feat-docs-home-refresh-getting-started

## Why

The Home page duplicates ~70 lines of installation steps verbatim with `installation.md` (already a drift risk for the git+ URLs), reads as documentation rather than a landing page, and its code blocks lack the symmetric vertical spacing the prose preset gives Markdown pages. Meanwhile Getting Started lacks the orientation pages a framework landing needs (what it is, when not to use it, how a project is laid out), and the #286 `@define_component` ergonomics change (optional derived names) is not yet reflected anywhere in the docs examples.

## What Changes

- **Home refresh**: restructure into hero (headline "Build Frontend in Python" + subtitle + two buttons: Get Started → `/documents/getting-started/what-is-webcompy`, View on GitHub), feature cards (reactivity / components & routing / CLI & SSR / PyScript runtime), a minimal single-`uv`-command teaser block with a "Full setup → Installation" link, and a source/footer strip. The duplicated detailed install sections (uv multi-block, Poetry, Lock File Commands table) are **removed** from Home — `installation.md` becomes the canonical source.
- **Symmetric code-block spacing on Home**: `Home` scoped style adds `margin: var(--space-4) 0` to `.code-block` (same value as `.prose pre` from #249), matching Markdown-page rhythm without adopting `.prose` typography side effects.
- **Getting Started additions** (3 new Markdown pages under `/documents/getting-started/`): `what-is-webcompy` (dual-environment positioning, core promises), `why-webcompy` (honest Why / Why NOT — e.g. PyScript bundle size and ecosystem youth as cons), `project-structure` (app package, `webcompy_config.py`, `static/`, resources, lockfile at a glance).
- **Refresh of existing pages**: `installation.md` config snippet aligned with the current scaffold template (`server=WebComPyServerConfig(...)`, explained `dependencies_from`), clarified optional browser deps, expanded headings for a useful TOC; `quickstart.md` example moved to the recommended `@define_component()` derived-name form.
- **Cross-page example sweep for #286**: all remaining `@define_component("<explicit-name>")` doc examples switch to the derived form where derivable; `custom_elements.md` stale text (name-argument required / round-trip validation) updated to the optional-derivation contract.

## Capabilities

### New Capabilities

- `docs-site-home`: The docs_app landing page — hero, feature cards, teaser, deduplication from docs, and code-block spacing parity with the prose preset.

### Modified Capabilities

- `docs-site-documents`: Getting Started gains the three orientation pages (manifest entries + URLs); existing page refresh keeps structure.
- `docs-e2e`: Home test expectations follow the new structure (hero headline instead of the removed "What is WebComPy" section heading); new Getting Started pages get dedicated test files.

## Impact

- `docs_app/templates/home.py` (restructure + scoped spacing), `docs_app/pages/home.py`, `docs_app/components/ui.py` (possible new hero/feature-card helpers), `docs_app/documents/` (3 new `.md`, edits to `installation.md`, `quickstart.md`, `custom_elements.md` and other pages carrying old-style examples), `docs_app/docs_manifest.py` (3 new Getting Started entries), `docs_app/pages/document/` (new thin page wrappers), `e2e/docs/test_home.py` updated + new page tests
- No framework package changes. Examples-only edits keep docstrings untouched (docs are outside `packages/*/src`).

## Known Issues Addressed

The overview/spec-known-issues list is untouched; this change removes a documentation drift source (duplicated install instructions between Home and `installation.md`).

## Non-goals

- Rewriting Advanced/Basic pages beyond the `@define_component` example-form sweep
- Adding new demo apps or Examples pages (③-9)
- Translating any content (all English)
- Changing the Markdown rendering pipeline
