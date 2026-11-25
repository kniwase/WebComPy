# Design: feat-docs-api-reference

## Context

`scripts/check-docstrings.py` already resolves the public API surface exactly as the `api-docstrings` spec defines it: `__init__.py` re-export chains → definition sites in private modules, class public members, module summaries, PEP 224 constants, important-internals allowlist, exemptions (dunders, overloads, property setters). Strict enforcement is on; signatures are validated against docstrings by pydoclint. The reference layer can treat all of this as its data source.

## Goals / Non-Goals

**Goals:** module-grouped hand-authored reference pages grounded in generated skeletons; CI-checked drift; docstrings stay the single machine-verified truth.

**Non-Goals:** prose autogeneration, mkdocstrings-style extraction at docs build time, API Reference inside the SPA rendering pipeline beyond normal page rendering.

## Decisions

1. **Generator at build-prep time, output committed** — `scripts/generate_api_reference.py [--check]`:
   - imports the surface resolver from `check-docstrings.py` (refactor it into an importable module first, e.g. `scripts/_api_surface.py` shared by both — a pure tooling move, no runtime impact);
   - emits for each page group a Markdown skeleton: `## <Symbol>` heading, fenced signature (`func(a: int, *, b=None) -> str`), first docstring line, `Args/Returns/Raises` rendered from docstring sections, plus an `<!-- author: grouping prose & examples -->` marker for preserved hand prose;
   - `--check` regenerates in-memory and diffs against committed files (ignoring authored regions delimited by `<!-- author:start -->`/`<!-- author:end -->`), exiting non-zero on drift → wired into the CI openspec/lint job.
   - **Alternative rejected**: generate HTML at docs build time from live Python — PyScript-side introspection is heavy, SSR cost grows, and committed Markdown keeps diffs reviewable.
2. **Page groups (9)**: `core-app`, `core-components`, `core-elements`, `core-signal`, `core-template`, `core-router-di`, `core-data` (ajax/aio/forms/storage/events), `ui` (theme/code block/components/styles), `server-cli` (webcompy_server + webcompy_cli + rpc + hydration + ports), `testing` — final grouping settled in the authoring task; each page frontmatter `title` "… API", `description` with module name.
3. **Ordering discipline on generated entries**: alphabetical within a page (reference lookup UX), with the checker page itself noting deliberate exceptions for closely-related symbol clusters.
4. **Prose layer**: per symbol only what docstrings must not carry — cross-links to Basic/Advanced pages, "see also", deprecation notes; kept inside author regions so regeneration never clobbers.
5. **Category placement**: `API Reference` last in `DOCS_SECTIONS`, prefix `/documents/api/`.

## Risks / Trade-offs

- [Regeneration churn creating noisy diffs] → `--check` fails only on real API drift; skeleton edits land in one commit with the API change.
- [Resolver duplication between checker and generator] → shared `scripts/_api_surface.py` extraction with checker regression tests unchanged.
- [Reference pages balloon sidebar] → one category, 9-10 pages; symbol-level TOC comes free from heading ids + `doc.toc`.

## Migration Plan

Merge last (all pages it links exist). Initial authoring is incremental per page group (tasks list them individually); partial category is acceptable mid-flight.

## Open Questions

None.
