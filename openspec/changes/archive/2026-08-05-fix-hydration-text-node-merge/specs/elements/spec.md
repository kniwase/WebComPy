## ADDED Requirements

### Requirement: Hydration SHALL normalize parser-merged text nodes to element-tree granularity before index-based adoption

`ElementWithChildren._hydrate_node()` SHALL NOT assume a pristine 1:1 correspondence between the element tree's child nodes and the browser DOM's `childNodes`. The HTML parser merges adjacent `#text` nodes during parsing, so a sequence of consecutive `TextElement` children (e.g. whitespace and interpolation holes adjacent in a composite body) can correspond to a single merged DOM `#text` node. Before per-child adoption proceeds by `_node_idx`, hydration SHALL detect a consecutive run of `TextElement` children and SHALL split the merged DOM `#text` node via `splitText(offset)` at the cumulative expected-text boundary of each child in the run, so that each element-tree child once again has a distinct DOM node at its `_node_idx`.

Normalization SHALL walk a **live DOM cursor**: runs SHALL be processed in element order at their current DOM position, re-reading `childNodes` as splits insert nodes, and SHALL NOT rely on indices or child counts computed before normalization began. This guarantees that a later run remains aligned after an earlier run was split, and that a run is never split using stale pre-normalization indices.

Normalization SHALL split at **every** boundary of a run, including zero-length boundaries, and SHALL detect an already-normalized run by checking that EVERY expected node (including empty ones) is present at its position — an empty trailing `TextElement` (`["a", ""]`, `["a", "", ""]`) SHALL receive its own `#text` node. A run whose children are all empty and whose DOM position has no `#text` node (the parser emits nothing for empty text) SHALL be materialized as one empty prerendered `#text` node per child, inserted at the run's position. `splitText` offsets SHALL be UTF-16 code-unit lengths (the browser `Text.splitText` unit), not Python code-point counts, so astral-plane characters split at the correct boundary.

Normalization SHALL be idempotent: when the DOM already has a 1:1 correspondence (no merging occurred, or splitting has already been applied), no further split SHALL be performed. Normalization SHALL apply only to the hydration path (`_hydrate_node`); server-side rendering, `_render`, refresh, reconcile, and positioning code SHALL remain unchanged.

When the merged DOM text content does not equal the concatenation of the run's expected text contents, hydration SHALL log a warning via `webcompy.logging.warning`, SHALL NOT split the run, and SHALL halt normalization for the remainder of that container so that the affected run (and everything after it) follows the existing per-node create/adopt fallback — the pre-fix behavior — rather than producing a misaligned split. No exception SHALL propagate to the caller.

This requirement applies to `ElementWithChildren._hydrate_node` (regular containers indexing from base `0`) and to dynamic-container hydration paths (`DynamicElement._hydrate_node`, `RepeatElement`, `FragmentElement`) that rely on the same index-based `childNodes` adoption. A `NewLine` (`<br>`) or `RawHTML` (wrapper element) child renders a non-`#text` DOM node and SHALL terminate a text run; only consecutive `TextElement` children participate in a run.

#### Scenario: Hydrating a fragment body with merged adjacent text
- **WHEN** a keyed loop item's body is a fragment containing `<span>` + a `TextElement` + another `TextElement`, and the browser parser has merged the two `#text` nodes into one
- **THEN** `_hydrate_node` SHALL split the merged DOM `#text` node at the cumulative expected-text boundary so each `TextElement` adopts its own `#text` node at the correct `_node_idx`
- **AND** subsequent reconcile/positioning SHALL observe a 1:1 element-to-DOM correspondence

#### Scenario: No merge leaves the DOM untouched
- **WHEN** hydration encounters children whose DOM `childNodes` already correspond 1:1 to the element tree (no adjacent text was merged)
- **THEN** `_hydrate_node` SHALL perform no `splitText` calls
- **AND** adoption SHALL proceed exactly as before this change

#### Scenario: Multiple merged runs in one container are all normalized
- **WHEN** a container has two separate runs of adjacent text separated by an element (e.g. `[a, b, <span>, c, d]` with the parser merging each run), and the second run's logical position is at or beyond the container's initial `childNodes` length
- **THEN** BOTH runs SHALL be split (the live DOM cursor keeps the second run aligned after the first split)

#### Scenario: Trailing empty text children receive their own nodes
- **WHEN** a text run ends in empty `TextElement` children (`["a", ""]` or `["a", "", ""]`) and the parser merged them into the preceding text
- **THEN** each empty child SHALL adopt its own empty `#text` node at its `_node_idx`

#### Scenario: All-empty text runs with no DOM node are materialized
- **WHEN** a run consists only of empty text children (the parser emits nothing for them, so no `#text` node exists at the run's position)
- **THEN** hydration SHALL insert one empty prerendered `#text` node per child at the run's position before adoption proceeds

#### Scenario: Astral text is split at UTF-16 boundaries
- **WHEN** a run splits non-BMP text (e.g. `["😀", "x"]` merged into one node)
- **THEN** the split SHALL occur at the UTF-16 code-unit boundary so each child adopts the correct text without rewriting

#### Scenario: Content mismatch falls back rather than mis-splitting
- **WHEN** the merged DOM `#text` content does not equal the concatenation of a text run's expected contents (e.g. unexpected prerendered content)
- **THEN** hydration SHALL skip splitting that run, log a warning, and halt normalization for the remainder of the container (pre-fix create/adopt fallback)
- **AND** no exception SHALL propagate to the caller

#### Scenario: Keyed ReactiveDict loop hydrates with a composite item body
- **WHEN** a `ReactiveDict` keyed loop renders items whose body contains multiple elements interleaved with text, and the prerendered HTML is parsed by the browser
- **THEN** hydration SHALL normalize the merged text nodes for every item
- **AND** a subsequent mutation that reorders keys SHALL reconcile children to the correct DOM positions without empty nodes or leftover prerendered nodes
