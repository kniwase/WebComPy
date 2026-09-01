# Design: feat-docs-home-refresh-getting-started

## Context

`docs_app/templates/home.py` is five `DocsSection` cards, two of which (uv / Poetry) are near-verbatim duplicates of `installation.md:10-71`; the installation page's `webcompy_config.py` snippet predates the current scaffold template and omits `server=`. The prose preset gained symmetric `pre` margins in #249 but Home is not `.prose`-wrapped, so its `CodeBlock`s sit at `margin:0`. `@define_component` since #286 accepts no name and derives the custom-element tag from the function name.

## Goals / Non-Goals

**Goals:** a landing Home that complements (not duplicates) docs; orientation pages; correct, current examples everywhere.

**Non-Goals:** component/page-framework rewrite of docs chrome; new demos; content beyond Getting Started category pages.

## Decisions

### 1. Home structure (single page, four bands)

```
[Hero]           h1 "Build Frontend in Python" + one-sentence subtitle
                 (reactive components, routing, SSR/SSG — all Python, runs
                 in the browser via PyScript)
                 buttons: Get Started → /documents/getting-started/what-is-webcompy
                          View on GitHub → repo URL
[Feature cards]  4 DocsCard tiles: Reactive by default / Components & Router /
                 CLI, SSR & SSG / PyScript runtime (numpy & friends)
[Teaser]         one bash CodeBlock (uv init + uv add + webcompy init) +
                 one python first-component snippet + "Full setup → Installation"
[Footer strip]   Source Code link, version note
```

- **Why cards instead of prose UL**: scannability; reuses `DocsCard`. **Rejected**: wrapping Home in `.prose` — would restyle headings/lists unexpectedly and blur landing vs document identity.
- The Poetry path stays only in `installation.md` (Home teaser shows the recommended uv path; a "Prefer Poetry? see Installation" line links across).

### 2. Code-block spacing parity via scoped rule

`Home.scoped_style` adds `".code-block": {"margin": "var(--space-4) 0"}`. Layer `webcompy-scope` beats `components` (where `code-block.css` sets `margin:0`), so the rule wins without `!important` and without touching global stylesheets. **Rejected**: changing `code-block.css` default margin — would affect every non-prose consumer (Examples cards, Docus-style embeds) and re-open the #249 layering decision.

### 3. Getting Started page set and order

| # | Path | Content skeleton |
|---|---|---|
| 1 | `.../what-is-webcompy` | what it is; dual-environment diagram (browser PyScript / server Python); core promises; relationship to FastAPI/starlette |
| 2 | `.../why-webcompy` | Why: Python-only stack, reactivity, SSG/SSR, typed RPC…; Why NOT (honest): PyScript payload size & cold start, browser-API gaps (no service-worker-free path etc. as applicable), young ecosystem, performance vs compiled JS |
| 3 | `.../installation` | existing, revised |
| 4 | `.../quickstart` | existing, revised |
| 5 | `.../project-structure` | app package layout, `webcompy_config.py` fields (build vs server), `static/`, resources allow-list, `webcompy-lock.json`, dist/ generated |

Why/Why NOT is one page (a reader deciding compares in one view); split later if length demands. **Rejected**: putting "What is" only on Home — docs need the canonical text; Home gets a summary card.

### 4. Installation/Quickstart revision specifics

- Config snippet updated to scaffold-template shape (incl. `server=WebComPyServerConfig(port=8080)`), each field one-line explained; keep git+ URLs with the "until PyPI" note.
- Heading expansion for TOC: `Prerequisites`, `Install with uv`, `Browser dependencies`, `Project configuration`, `Lock file & dev server`, `Install with Poetry`.
- Quickstart first component becomes `@define_component()` + `def HomePage(...)`; a note mentions the explicit `custom_element_name=` alternative for non-derivable cases.

### 5. Example sweep rule for #286

Convert `@define_component("x-y")` → `@define_component()` iff the function name derives the same tag (`PascalCase`→kebab round trip). Where docs intentionally show a mismatched function name (`Card` with tag `user-card`), keep the explicit kwarg named `custom_element_name=` per the new signature and update surrounding prose (the old "must match" sentence is gone; `custom_elements.md` stale round-trip validation text replaced by the derivation contract).

## Risks / Trade-offs

- [Removing Home install detail may annoy users who landed there first] → Hero + teaser route directly to Installation; acceptable.
- [Honest Why-NOT page ages badly if weaknesses are fixed] → Keep phrasing behavioral ("at the time of writing"), review trigger noted in tasks.
- [Two stacked spec deltas on `docs-site-documents` (this + restructure)] → Archive/merge order: `refactor-docs-sections-restructure` first (its category model defines the Getting Started prefix used here).

## Migration Plan

Docs-app content edits only; SSG regenerates. No URL changes except three new pages.

## Open Questions

None.
