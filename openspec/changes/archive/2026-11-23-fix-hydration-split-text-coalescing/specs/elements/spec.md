# Elements — Hydration Split-Text Coalescing Deltas

## MODIFIED Requirements

### Requirement: Hydration SHALL normalize parser-merged text nodes to element-tree granularity before index-based adoption

`ElementWithChildren._hydrate_node()` SHALL NOT assume a pristine 1:1 correspondence between the element tree's child nodes and the browser DOM's `childNodes`. The HTML parser merges adjacent `#text` nodes during parsing, so a sequence of consecutive `TextElement` children (e.g. whitespace and interpolation holes adjacent in a composite body) can correspond to a single merged DOM `#text` node. Before per-child adoption proceeds by `_node_idx`, hydration SHALL detect a consecutive run of `TextElement` children and SHALL split the merged DOM `#text` node via `splitText(offset)` at the cumulative expected-text boundary of each child in the run, so that each element-tree child once again has a distinct DOM node at its `_node_idx`.

Normalization SHALL walk a **live DOM cursor**: runs SHALL be processed in element order at their current DOM position, re-reading `childNodes` as splits insert nodes, and SHALL NOT rely on indices or child counts computed before normalization began. This guarantees that a later run remains aligned after an earlier run was split, and that a run is never split using stale pre-normalization indices.

Normalization SHALL split at **every** boundary of a run, including zero-length boundaries, and SHALL detect an already-normalized run by checking that EVERY expected node (including empty ones) is present at its position — an empty trailing `TextElement` (`["a", ""]`, `["a", "", ""]`) SHALL receive its own `#text` node. A run whose children are all empty and whose DOM position has no `#text` node (the parser emits nothing for empty text) SHALL be materialized as one empty prerendered `#text` node per child, inserted at the run's position. `splitText` offsets SHALL be UTF-16 code-unit lengths (the browser `Text.splitText` unit), not Python code-point counts, so astral-plane characters split at the correct boundary.

Conversely, when pre-hydration DOM mutations leave two or more consecutive DOM `#text` nodes at a text element or text-run position (including a single non-empty `TextElement` whose text was fragmented across adjacent `#text` nodes, or a multi-`TextElement` run whose DOM `#text` boundaries differ from the element tree) and their concatenated text equals the run's expected text, normalization SHALL coalesce those consecutive `#text` nodes into a single `#text` node before per-child adoption or `splitText` splitting proceeds. When any node in the coalesced DOM `#text` slice carried prerendered status, the coalesced node SHALL retain that prerendered status, and the extra adjacent `#text` siblings SHALL be removed. When the concatenated DOM `#text` content does not equal the run's expected text, coalescing SHALL NOT occur.

Normalization SHALL be idempotent: when the DOM already has a 1:1 correspondence (no merging or splitting occurred, or normalization has already been applied), no writes, removals, or further splits SHALL be performed. Normalization SHALL apply only to the hydration path (`_hydrate_node`); server-side rendering, `_render`, refresh, reconcile, and positioning code SHALL remain unchanged.

When the concatenated DOM text content of consecutive `#text` nodes at a multi-node run position does not equal the concatenation of the run's expected text contents, hydration SHALL record a `text` mismatch (see the hydration-mismatch diagnostics requirement below), SHALL NOT coalesce or split the run, and SHALL halt normalization for the remainder of that container so that the affected run (and everything after it) follows the existing per-node create/adopt fallback — the pre-fix behavior — rather than producing a misaligned split. When a non-`#text` node occupies a text-run position, hydration SHALL record a `tag` mismatch with the expected identity `#text` and the owning component ID when known. No exception SHALL propagate to the caller.

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
- **THEN** hydration SHALL skip splitting that run and halt normalization for the remainder of the container (pre-fix create/adopt fallback)
- **AND** a `text` mismatch record SHALL be created for the run
- **AND** no exception SHALL propagate to the caller

#### Scenario: A non-text node at a text-run position is a structural mismatch
- **WHEN** a DOM node whose `nodeName` is not `#text` occupies a text-run position
- **THEN** hydration SHALL record a `tag` mismatch with expected identity `#text` and the actual node name
- **AND** the owning component ID SHALL be attached when known
- **AND** normalization SHALL halt for the remainder of the container

#### Scenario: Keyed ReactiveDict loop hydrates with a composite item body
- **WHEN** a `ReactiveDict` keyed loop renders items whose body contains multiple elements interleaved with text, and the prerendered HTML is parsed by the browser
- **THEN** hydration SHALL normalize the merged text nodes for every item
- **AND** a subsequent mutation that reorders keys SHALL reconcile children to the correct DOM positions without empty nodes or leftover prerendered nodes

#### Scenario: Single non-empty text node coalesces externally split consecutive text nodes
- **WHEN** a single non-empty `TextElement` corresponds to multiple consecutive DOM `#text` nodes whose concatenated text equals the element's expected text (for example after an external pre-hydration DOM mutation replaced a substring with a newly created `#text` node)
- **THEN** normalization SHALL coalesce those consecutive `#text` nodes into a single `#text` node while preserving prerendered status if any coalesced node carried prerendered status
- **AND** adoption SHALL proceed without recording any hydration mismatch, keeping subsequent sibling elements aligned at their expected `_node_idx`

#### Scenario: Multi-part text run coalesces and re-splits mismatched text boundaries
- **WHEN** a consecutive run of `TextElement` children does not match the DOM nodes 1:1, and the DOM position holds multiple consecutive `#text` nodes whose concatenated text equals the concatenation of the run's expected texts
- **THEN** normalization SHALL coalesce those consecutive `#text` nodes and split at the expected element-tree boundaries so each `TextElement` adopts its `#text` node without recording any hydration mismatch

#### Scenario: Already aligned text run ignores trailing stray text node
- **WHEN** a consecutive run of `TextElement` children already matches its corresponding prefix of DOM `#text` nodes 1:1 and an extra unexpected `#text` node immediately follows in the container
- **THEN** normalization SHALL leave the matched DOM `#text` nodes untouched without rewriting their text or coalescing the trailing stray node
- **AND** container excess-node handling SHALL detect the structural node-count mismatch as before
