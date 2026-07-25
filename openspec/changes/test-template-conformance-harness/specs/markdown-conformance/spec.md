# Delta Spec: markdown-conformance (new capability)

## ADDED Requirements

### Requirement: The framework shall declare GFM as the Markdown conformance target

`DefaultMarkdownParser` SHALL target conformance with the GitHub Flavored Markdown specification: CommonMark plus the GFM extensions (tables, task list items, strikethrough, autolinks, disallowed raw HTML). The harness SHALL pin the conformance target to a specific cmark-gfm commit by recording the commit URL and SHA-256 hash of the official `spec.txt` as code constants. The spec TEXT itself SHALL NOT be committed to the repository (it is derived from the CC BY-SA 4.0 CommonMark spec); the harness SHALL download, hash-verify, and cache the file on first use. Current deviations from the target SHALL be explicitly listed as scheduled for removal in the parser-rewrite changes.

#### Scenario: Conformance target is discoverable
- **WHEN** a developer inspects the conformance harness module
- **THEN** the pinned cmark-gfm commit URL and SHA-256 hash SHALL be recorded as constants
- **AND** the list of currently-deviating behaviors SHALL be recorded in this spec

#### Scenario: Known deviations scheduled for removal
- **WHEN** the conformance suite runs against the current parser
- **THEN** deviations including space-less ATX headings (`#hashtag` producing `<h1>`), ignored fenced-code info strings, tab normalization to 2 spaces, missing setext headings, paragraph line-joining (current parser joins lines with a space; GFM preserves the newline), mixed list-marker coalescing (current parser merges `-`/`*`/`+` and `1.`/`2)` into a single list; GFM splits them), blockquote multiline joining (current parser joins lines as inline text; GFM wraps them in `<p>`), and missing GFM extensions SHALL be tracked as scheduled for removal (not as accepted behavior)

### Requirement: GFM spec examples shall run as a parametrized test suite

The official GFM `spec.txt` SHALL be fetched on-demand (per the harness download policy), hash-verified, cached under `tests/conformance/.tmp/` (gitignored), and parsed at test-collection time into one parametrized pytest case per example. Each case executes `DefaultMarkdownParser.render()` on the example input and compares against the example's expected HTML. Comparison normalization SHALL be limited to trailing whitespace/newline handling and SHALL be defined in the harness, never in the parser.

#### Scenario: Example extraction
- **WHEN** pytest collects `tests/conformance/`
- **THEN** every numbered example in the cached `spec.txt` SHALL produce exactly one test case identified by its example number and section name

#### Scenario: Offline execution after initial fetch
- **WHEN** the conformance suite runs in CI (or locally) and the cache file already exists
- **THEN** all conformance tests SHALL execute without network access (the cache is reused as-is)

#### Scenario: Cache-miss with network failure fails loudly
- **WHEN** the cache file is missing and the network is unavailable
- **THEN** the harness SHALL fail the test run with a clear error message instructing the user to populate the cache (it SHALL NOT silently skip)

#### Scenario: No parser-side special-casing
- **WHEN** an example fails due to output formatting differences
- **THEN** the harness SHALL NOT compensate beyond its documented normalization; the example SHALL be recorded as failing

### Requirement: Conformance failures shall be tracked as strict xfails

Every failing spec example SHALL be listed by number in a checked-in xfail list and marked with `pytest.mark.xfail(strict=True)`. An example that begins passing while still listed SHALL fail the suite until removed from the list, making conformance improvements explicit, reviewable diffs. A non-failing summary test SHALL report the current pass rate.

#### Scenario: Improvement flips an xfail
- **WHEN** a parser change makes a previously-failing example pass
- **THEN** the strict xfail SHALL fail the suite
- **AND** the developer SHALL remove that example number from the xfail list in the same change

#### Scenario: Conformance rate visible
- **WHEN** the conformance suite completes
- **THEN** the current pass/total count SHALL be reported (e.g., via the summary test's output) without failing the suite

### Requirement: Tests pinning GFM deviations shall be marked for retirement

Existing parser tests that assert behavior contradicting the GFM spec SHALL be marked with `pytest.mark.gfm_deviation` and enumerated in this spec. They SHALL remain active while the current parser exists and SHALL be removed by the parser-rewrite changes.

#### Scenario: Deviation tests identifiable
- **WHEN** a developer runs `pytest -m gfm_deviation`
- **THEN** exactly the deviation-pinning tests SHALL be selected (e.g., space-less headings, ignored fence language, tab-to-2-spaces)

### Requirement: HTML template parsing shall be environment-parity verified

The template engine SHALL produce identical Element trees for version-sensitive inputs (`<textarea>`, `<title>`, `<pre>`, character-reference edge cases, `<plaintext>`) on the server (CPython) and in the browser (Pyodide). Parity SHALL be verified by a permanent E2E scenario comparing server-rendered and browser-rendered results for the same template set. If divergence is detected, the template parser SHALL pin the behavior framework-side (e.g., explicit RCDATA handling) so parsing no longer depends on stdlib version.

#### Scenario: Parity regression guard
- **WHEN** the parity E2E scenario runs
- **THEN** the browser-produced tree for each version-sensitive template SHALL match the server-produced tree

#### Scenario: Divergence triggers pinning
- **WHEN** the parity check detects a divergence (e.g., `<textarea><b>x</b></textarea>` parsed differently)
- **THEN** the template parser SHALL be modified to handle RCDATA elements explicitly, independent of stdlib version
- **AND** the parity scenario SHALL pass afterward
