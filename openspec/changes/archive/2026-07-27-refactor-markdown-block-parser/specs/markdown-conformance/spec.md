# Delta Spec: markdown-conformance

## MODIFIED Requirements

### Requirement: The framework shall declare GFM as the Markdown conformance target

`DefaultMarkdownParser` SHALL target conformance with the GitHub Flavored Markdown specification: CommonMark plus the GFM extensions (tables, task list items, strikethrough, autolinks, disallowed raw HTML). The vendored copy of the official GFM `spec.txt` SHALL record its spec revision in a header comment. Current deviations from the target SHALL be explicitly listed as scheduled for removal in the parser-rewrite changes. Deviations retired by a rewrite change SHALL be removed from this list in the same change.

#### Scenario: Conformance target is discoverable
- **WHEN** a developer inspects the conformance harness directory
- **THEN** the vendored `spec.txt` SHALL identify its GFM spec revision
- **AND** the list of currently-deviating behaviors SHALL be recorded in this spec

#### Scenario: Known deviations scheduled for removal
- **WHEN** the conformance suite runs against the current parser
- **THEN** remaining deviations (inline-level: emphasis/strong delimiter handling, code spans, link/image details, entity references, hard breaks, raw inline HTML, autolinks, strikethrough conformance, disallowed raw HTML) SHALL be tracked as scheduled for removal in `refactor-markdown-inline-parser`
- **AND** block-level deviations (headings, tabs, blockquotes, lists, code blocks, HTML blocks, link reference definitions, thematic breaks, tables, task list items) SHALL have been removed by this change

#### Scenario: Block-section xfails flipped
- **WHEN** this change completes
- **THEN** every strict xfail in the conformance suite attributable to block structure SHALL have been removed (passing)
- **AND** any remaining xfail in block test sections SHALL carry a note that its cause is inline-level
