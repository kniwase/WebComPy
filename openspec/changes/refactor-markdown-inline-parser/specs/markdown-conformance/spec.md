# Delta Spec: markdown-conformance

## MODIFIED Requirements

### Requirement: The framework shall declare GFM as the Markdown conformance target

`DefaultMarkdownParser` SHALL conform to the GitHub Flavored Markdown specification: CommonMark plus the GFM extensions (tables, task list items, strikethrough, autolinks, disallowed raw HTML). Conformance is measured against the vendored GFM spec suite: **654/672 examples pass (97.3%)**, with 18 remaining examples documented as known deviations. These deviations fall into three categories: (1) cmark-gfm emphasis divergence where the parser matches the broader ecosystem (commonmark.js/py, markdown-it) over cmark-gfm's idiosyncratic residual-delimiter collapse (9 examples), (2) harness artifact where GFM extensions always-on causes CommonMark-base examples to diverge (2 examples), and (3) pre-existing block-layer edge cases inherited from the prior refactor (6 examples) plus one obscure inline-raw-HTML edge case (1 example). The vendored copy of the official GFM `spec.txt` SHALL record its spec revision in a header comment.

#### Scenario: Conformance suite substantially reduced
- **WHEN** this change completes
- **THEN** the strict-xfail list SHALL be reduced from 295 to 18
- **AND** each remaining xfail SHALL carry an accurate note describing the root cause and scope

#### Scenario: Deviation list documented
- **WHEN** a developer inspects the conformance records
- **THEN** each remaining deviation SHALL be listed with its root cause
- **AND** the `gfm_deviation` marker SHALL NOT be reintroduced
- **AND** deviations SHALL be traceable to either: (a) cmark-gfm emphasis divergence matching ecosystem, (b) harness/extension-application artifact, or (c) out-of-scope inherited block-layer issues

#### Scenario: Template-syntax protection preserved
- **WHEN** code spans or code blocks contain `{{ }}` or `{% %}` text
- **THEN** the rendered `<code>`/`<pre>` content SHALL be literal (no interpolation, no directive execution)
- **AND** context values SHALL never appear inside code output (structurally guaranteed: code content never enters inline/template processing)
