# Delta Spec: markdown-conformance

## MODIFIED Requirements

### Requirement: The framework shall declare GFM as the Markdown conformance target

`DefaultMarkdownParser` SHALL conform to the GitHub Flavored Markdown specification: CommonMark plus the GFM extensions (tables, task list items, strikethrough, autolinks, disallowed raw HTML). Conformance is defined as **full pass of the vendored GFM spec suite** — the strict-xfail list SHALL be empty on completion of this change. The vendored copy of the official GFM `spec.txt` SHALL record its spec revision in a header comment.

#### Scenario: Conformance suite fully passes
- **WHEN** this change completes
- **THEN** every example in the vendored GFM spec suite SHALL pass
- **AND** the xfail list SHALL be empty (no tracked deviations remain)

#### Scenario: Deviation list emptied
- **WHEN** a developer inspects the conformance records
- **THEN** no behavior SHALL be listed as a known deviation
- **AND** no test SHALL carry the `gfm_deviation` marker

#### Scenario: Template-syntax protection preserved
- **WHEN** code spans or code blocks contain `{{ }}` or `{% %}` text
- **THEN** the rendered `<code>`/`<pre>` content SHALL be literal (no interpolation, no directive execution)
- **AND** context values SHALL never appear inside code output (structurally guaranteed: code content never enters inline/template processing)
