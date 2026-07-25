# Proposal: test-template-conformance-harness

## Why

The project committed to rebuilding the Markdown parser as a multi-stage parser targeting full GFM (GitHub Flavored Markdown) spec conformance, but there is currently no objective way to measure conformance: the existing Markdown tests pin several intentional *deviations* from CommonMark as if they were specifications (space-less headings, ignored fence languages, tab-equals-2-spaces). Separately, the HTML template parser relies on stdlib `html.parser` behavior that varies across Python builds (RCDATA handling of `<textarea>`/`<title>`), creating a risk of SSR/browser AST divergence that breaks hydration — and this risk is currently unverified. Before the rewrite begins, the project needs a conformance measurement baseline, a cross-environment parity check, and an explicit inventory of which current behaviors are intentional limitations versus defects scheduled for removal.

## What Changes

- Add a GFM spec-test harness: pin the official GFM `spec.txt` to a specific cmark-gfm commit (CommonMark 652 examples + GFM extension examples) via constants in the harness module, download it on-demand at first use with SHA-256 verification, cache it under `tests/conformance/.tmp/` (gitignored), and extract examples into a parametrized pytest suite that runs them against `DefaultMarkdownParser.render()`, reporting the conformance rate. The spec content is not committed to the repository (CC BY-SA 4.0 licensing concern). All failing examples start as individually-tracked xfails.
- Inventory existing Markdown tests that pin deviations from CommonMark/GFM and mark them as retirement candidates for the follow-up parser-rewrite changes.
- Add cross-environment `html.parser` parity verification: an E2E-level check that templates containing `<textarea>`/`<title>` (and other version-sensitive constructs) produce identical element trees on server and in the browser. **If** divergence is found, pin behavior framework-side by defining `CDATA_CONTENT_ELEMENTS`/RCDATA handling in the template parser subclass (implementation included in this change only if needed).
- Document intentional template-engine limitations in the `template-engine` spec: expression language restricted to identifier/dot paths, `{% for %}` semantics (one-variable dict iteration yields values; two-variable requires a dict), `:root`/`html`/`body` scoped-CSS dead rules, duplicate CSS keys last-wins, `@import`/`@charset` dropped, keyframe names global, SVG/MathML case corruption, `textwrap.dedent` interaction with `<pre>`, no `{# #}` comments, no literal-`{{` escape, entity-decoded holes.
- Declare GFM (CommonMark + tables, task list items, strikethrough, autolinks, disallowed raw HTML) as the conformance target of `DefaultMarkdownParser` in the spec, with current deviations listed as scheduled for removal.

### Non-goals

- Rewriting the Markdown parser (follow-up changes `refactor-markdown-block-parser` / `refactor-markdown-inline-parser`).
- Reducing the xfail count (the harness measures; the rewrites fix).
- docs_app user-facing documentation (part of `refactor-markdown-inline-parser`).
- Any new template/Markdown feature.

## Known Issues Addressed

- Adds the SSR/browser `html.parser` version-drift risk (previously only noted in audit findings) to the tracked agenda; either disproves it or fixes it via framework-side pinning.

## Capabilities

### New Capabilities

- `markdown-conformance`: GFM spec-test harness, conformance measurement, deviation inventory, and the declaration of GFM as the parser's conformance target.

### Modified Capabilities

- `template-engine`: Intentional limitations documented (expression language, `{% for %}` semantics, CSS scoping limits, HTML parsing limits); HTML parser environment-parity requirement added.
- `test-execution-paths`: The conformance harness placement and execution mode (unit-test tier, offline, no network) aligned with the existing test-separation rules.

## Impact

- **Code**: `tests/` (new harness module + parity tests; possible small pinning fix in `packages/webcompy/src/webcompy/template/_parser.py` if parity fails). No spec.txt content is committed; only a pinned URL and SHA-256 hash as code constants.
- **Specs**: new `markdown-conformance`; modified `template-engine`, `test-execution-paths`.
- **No user-facing behavior change** unless the parity fix is triggered.
- **E2E**: one new browser parity scenario (uses existing inspect/E2E infrastructure).
